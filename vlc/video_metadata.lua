-- SPDX-License-Identifier: GPL-2.0-only
-- Copyright and licensing scope: see COPYRIGHT.md in the project root.
-- Linux VLC 3 extension. Installation injects paths and release metadata below.
local VERSION, BUILD_DATE = 'development', 'unreleased'
-- @CONFIG@
local dialog, status, filename, append_genre
local fields, presets, legacy, baseline = {}, {}, {}, {}
local clears, new_tags = {}, {}
local quick_tag_editing = false
local names = {'artist', 'album', 'genre'}
local current, pending, sequence = nil, nil, 0
local load_error, backup_review

-- Small rotating diagnostic log: actions and stages only, no tag contents.
local function trace(event)
    pcall(function()
        local path = SUPPORT_DIR .. '/activity.log'
        local file = io.open(path, 'ab')
        if not file then return end
        local size = file:seek('end')
        if size and size > 131072 then
            file:close()
            if not os.rename(path, path .. '.1') then return end
            file = io.open(path, 'ab')
            if not file then return end
        end
        file:write(os.date('!%Y-%m-%dT%H:%M:%SZ') .. ' ' .. event .. '\n')
        file:close()
    end)
end
local function traced(name, callback)
    return function(...)
        trace('begin ' .. name)
        local ok, result = pcall(callback, ...)
        trace((ok and 'end ' or 'error ') .. name)
        if not ok then error(result) end
        return result
    end
end
local function cancel_read()
    if not pending or pending.mode ~= 'read' then return end
    local file = io.open(pending.job .. '/cancel', 'wb')
    if file then file:close(); trace('cancel read') end
end

function descriptor()
    return {title='Metadata Pro', version=VERSION, author='Video Metadata',
        capabilities={'input-listener', 'menu'},
        shortdesc='Metadata Pro', description='Space-separated Artist, Album and Genre values.'}
end
local function html(s)
    return tostring(s):gsub('&', '&amp;'):gsub('<', '&lt;'):gsub('>', '&gt;')
end
local function wrap_status(s)
    -- Bound unbroken filenames and log paths in the status panel; split UTF-8
    -- only between characters.
    local lines = {}
    for line in (tostring(s) .. '\n'):gmatch('(.-)\n') do
        local chars = {}
        for char in line:gmatch('[%z\1-\127\194-\244][\128-\191]*') do
            chars[#chars + 1] = char
        end
        local first = 1
        while #chars - first + 1 > 80 do
            local last = first + 79
            local space
            for i = last + 1, first + 1, -1 do
                if chars[i] == ' ' then space = i; break end
            end
            if space then
                lines[#lines + 1] = html(table.concat(chars, '', first, space - 1))
                first = space + 1
            else
                lines[#lines + 1] = html(table.concat(chars, '', first, last))
                first = last + 1
            end
        end
        lines[#lines + 1] = html(table.concat(chars, '', first))
    end
    return lines
end
local function message(s)
    local lines = wrap_status(s)
    -- Reserve six lines for ordinary messages; show every line of longer errors.
    while #lines < 6 do lines[#lines + 1] = '&nbsp;' end
    status:set_text('<b>' .. table.concat(lines, '<br>') .. '</b>')
end
local function load_failed(s)
    load_error = s
    message(s)
end
local function encode(s)
    return (s:gsub('([^%w%-%._~])', function(c) return string.format('%%%02X', c:byte()) end))
end
local function decode(s) return (s:gsub('%%(%x%x)', function(h) return string.char(tonumber(h,16)) end)) end
local function quote(s) return "'" .. s:gsub("'", "'\\''") .. "'" end
local function whitespace(s)
    -- Match Python's Unicode whitespace splitting, including nonbreaking spaces.
    return (s:gsub('\194\133', ' '):gsub('\194\160', ' ')
        :gsub('\225\154\128', ' '):gsub('\226\128[\128-\138]', ' ')
        :gsub('\226\128[\168\169\175]', ' '):gsub('\226\129\159', ' ')
        :gsub('\227\128\128', ' '):gsub('[\028-\031]', ' '))
end
local function dirty()
    for _, key in ipairs(names) do
        if clears[key]:get_checked() then return true end
        if fields[key]:get_text() ~= (baseline[key] or '') then return true end
    end
    return false
end
local function launch(values, cache_item)
    backup_review = nil
    sequence = sequence + 1
    local job = SUPPORT_DIR .. '/jobs/' .. tostring(os.time()) .. '-' .. tostring(math.random(100000,999999)) .. '-' .. sequence
    if vlc.io.mkdir(job, '0700') ~= 0 then message('Cannot create job directory.'); return end
    local file, err = io.open(job .. '/request.txt', 'wb')
    if not file then message(tostring(err)); return end
    for key, value in pairs(values) do file:write(key .. '=' .. encode(value) .. '\n') end
    if not file:close() then message('Could not write request.'); return end
    local command = quote(PYTHON) .. ' ' .. quote(SUPPORT_DIR .. '/run_worker.py') .. ' ' .. quote(job) ..
        ' >>' .. quote(job .. '/worker.log') .. ' 2>&1 &'
    trace('launch ' .. values.mode)
    local code = os.execute(command)
    trace('launched ' .. values.mode)
    if code ~= 0 and code ~= true then message('Could not launch helper.'); return end
    pending = {job=job, mode=values.mode, path=values.file, snapshot={}, clear_snapshot={}, cache_item=cache_item}
    for _, key in ipairs(names) do
        pending.snapshot[key] = fields[key]:get_text()
        pending.clear_snapshot[key] = clears[key]:get_checked()
    end
    message('Working. Click Check status shortly. Edits made while saving remain unsaved.')
end
local function target_uri()
    -- Query the playlist first: an extension input reference can lag behind it.
    -- This also works when stopping playback destroys the active input.
    if vlc.playlist.current and vlc.playlist.get then
        trace('playlist current')
        local id = vlc.playlist.current()
        if type(id) == 'number' and id >= 0 then
            trace('playlist get')
            local entry = vlc.playlist.get(id)
            trace('playlist ready')
            if entry and entry.path and entry.path ~= '' then return entry.path end
        end
    end
    local item = vlc.input.item()
    if item then return item:uri() end
    -- The displayed target stays usable even if VLC has cleared its playlist.
    return pending and pending.path or current and current.path
end
local function local_path(uri)
    if type(uri) ~= 'string' then return nil end
    if uri:sub(1, 1) == '/' then return uri end
    if uri:lower():match('^file://') then return vlc.strings.make_path(uri) end
    return nil
end
function load_current()
    backup_review = nil
    if pending and pending.mode == 'backups_preview' then pending.cancelled = true end
    local uri = target_uri()
    local path = local_path(uri)
    local displayed_path = pending and pending.path or current and current.path
    if displayed_path and path ~= displayed_path then
        -- Clear is a one-file action, not a preference for subsequent files.
        -- Reset before the unsaved-text guard, even while a save is running.
        for _, key in ipairs(names) do
            clears[key]:set_checked(false)
            if pending and pending.mode == 'save' then
                -- The submitted request is already on disk. This UI reset is
                -- not a user cancellation of the clear that was submitted.
                pending.clear_snapshot[key] = false
            end
        end
    end
    if pending then
        if pending.mode ~= 'read' or pending.path == path then
            local previous_path = pending.path
            check_status(false)
            if pending or previous_path == path then return end
            -- A completed save must not swallow the request to load the next file.
        end
        -- A read is harmless to abandon. Never apply its old-file result to a
        -- new Load current video request, and never abandon an in-progress save.
        cancel_read()
        pending = nil
    end
    if dirty() then
        message('Unsaved changes. Click Discard edits, then Load current video to switch files.'); return
    end
    current, load_error = nil, nil
    baseline, legacy = {}, {}
    for _, key in ipairs(names) do
        fields[key]:set_text('')
        clears[key]:set_checked(false)
    end
    reload_presets()
    filename:set_text(html(path or uri or 'No file loaded'))
    if not uri then
        load_failed('No video is available in VLC. Open a video and pause it, then click Load current video.'); return
    end
    local original = path and (path:match('^(.*)%.[bB][aA][kK]$') or
        path:match('^(.*)%.[bB][aA][kK]%.%d+$'))
    if original and (original:lower():match('%.mp4$') or original:lower():match('%.mkv$')) then
        load_failed('VLC selected a backup copy. Open the original video, then click Load current video and Check status:\n' .. original)
        return
    end
    if not path or not (path:lower():match('%.mp4$') or path:lower():match('%.mkv$')) then
        load_failed('This item is not a supported local MP4 or MKV: ' .. tostring(uri)); return
    end
    local cache_item = vlc.input.item()
    if cache_item and local_path(cache_item:uri()) ~= path then cache_item = nil end
    launch({file=path, mode='read'}, cache_item)
end
function input_changed()
    backup_review = nil
    if not dialog then return end
    local path = local_path(target_uri())
    if path and path == (pending and pending.path or current and current.path) then return end
    load_current()
end
function discard_edits()
    if pending then message('Check the running operation first.'); return end
    for _, key in ipairs(names) do
        fields[key]:set_text(baseline[key] or '')
        clears[key]:set_checked(false)
    end
    message('Edits discarded. Load current video to switch files.')
end
local function preset_line(line)
    return line:gsub('^\239\187\191', ''):match('^%s*(.-)%s*$')
end
local function refresh_preset(key, problems)
    local preset = presets[key]
    -- Keep the list widget alive: deleting it can block on VLC's Qt thread.
    preset.widget:clear()
    preset.values = {}
    preset.widget:add_value('(select a value)', 1)
    local file = io.open(SUPPORT_DIR .. '/config/' .. key .. 's.txt', 'rb')
    if file then
        local seen = {}
        for line in file:lines() do
            line = preset_line(line)
            if line ~= '' and line:sub(1, 1) ~= '#' then
                if whitespace(line):find('%s') then
                    table.insert(problems, key .. ': skipped preset containing whitespace')
                elseif not seen[line] then
                    seen[line] = true
                    table.insert(preset.values, line)
                    preset.widget:add_value(line, #preset.values + 1)
                end
            end
        end
        file:close()
    end
end
function reload_presets()
    local problems = {}
    for _, key in ipairs(names) do refresh_preset(key, problems) end
    message(#problems > 0 and table.concat(problems, '\n') or 'Presets loaded.')
end
local function load_settings()
    local enabled = false
    quick_tag_editing = false
    local file = io.open(SUPPORT_DIR .. '/config/settings.txt', 'rb')
    if file then
        for line in file:lines() do
            local key, value = preset_line(line):match('^(%w[%w_]*)%s*=%s*(%a+)$')
            if key == 'append_genre_to_album' then enabled = value == 'true' end
            if key == 'quick_tag_editing' then quick_tag_editing = value == 'true' end
        end
        file:close()
    end
    return enabled
end
-- Small config writes stay synchronous; video work remains in the background.
-- A same-directory lock serializes extension writers, and rename commits only
-- a complete file. Existing comments/order survive; failed writes keep the original.
local function update_config(name, transform)
    local path = SUPPORT_DIR .. '/config/' .. name
    local lock = path .. '.lock'
    if vlc.io.mkdir(lock, '0700') ~= 0 then
        return nil, 'Cannot lock ' .. name .. '. Check permissions or another editor instance.'
    end
    local temporary = lock .. '/value.tmp'
    local ok, result = pcall(function()
        local file, err, code = io.open(path, 'rb')
        local contents = ''
        if file then
            contents, err = file:read('*a')
            file:close()
            if not contents then error(err or 'Cannot read configuration') end
        elseif code ~= 2 then
            error(err or 'Cannot read configuration')
        end
        local updated = transform(contents)
        if updated == contents then return end
        local output, problem = io.open(temporary, 'wb')
        if not output then error(problem) end
        local written, write_error = output:write(updated)
        local closed, close_error = output:close()
        if not written or not closed then error(write_error or close_error or 'Cannot write configuration') end
        local renamed, rename_error = os.rename(temporary, path)
        if not renamed then error(rename_error) end
    end)
    os.remove(temporary)
    os.remove(lock)
    return ok, result
end
local function save_album_setting(value)
    return update_config('settings.txt', function(contents)
        local found = false
        local newline = contents:find('\r\n', 1, true) and '\r\n' or '\n'
        if contents ~= '' and contents:sub(-1) ~= '\n' then contents = contents .. newline end
        local updated = contents:gsub('([^\n]*)(\n)', function(line, ending)
            local bom = line:match('^\239\187\191') or ''
            local body = line:sub(#bom + 1)
            local prefix, suffix = body:match('^(%s*append_genre_to_album%s*=%s*)%a+(%s*)$')
            if prefix then
                found = true
                return bom .. prefix .. value .. suffix .. ending
            end
            return line .. ending
        end)
        if not found then updated = updated .. 'append_genre_to_album=' .. value .. newline end
        return updated
    end)
end
local function append_values(key, selected)
    local text, seen, entries = whitespace(fields[key]:get_text()), {}, {}
    for token in text:gmatch('%S+') do
        if not seen[token] then table.insert(entries, token); seen[token] = true end
    end
    for _, value in ipairs(selected) do
        if not seen[value] then table.insert(entries, value); seen[value] = true end
    end
    fields[key]:set_text(table.concat(entries, ' '))
end
local function create_preset(key)
    if not quick_tag_editing then return end
    if pending then message('An operation is running. Click Check status.'); return end
    if not current then message('Load current video and Check status first.'); return end
    if clears[key]:get_checked() then message('Uncheck Clear on Save before adding values.'); return end
    if legacy[key] and fields[key]:get_text() == baseline[key] then
        message('This field has existing values containing whitespace. Type a replacement first.'); return
    end
    local value = new_tags[key]:get_text()
    if value == '' then
        message('Enter one tag, for example Pink_Floyd.'); return
    end
    if whitespace(value):find('%s') then
        message("Spaces and tabs aren't allowed in a single tag. Use Pink_Floyd instead of Pink Floyd."); return
    end
    if value:sub(1, 1) == '#' or value:find('[%z\1-\31\127]') or
            value:find('\239\187\191', 1, true) or value:find('\239\191[\190\191]') then
        message('A preset cannot start with # or contain control characters.'); return
    end
    local ok, err = update_config(key .. 's.txt', function(contents)
        for line in (contents .. '\n'):gmatch('(.-)\n') do
            if preset_line(line) == value then return contents end
        end
        local newline = contents:find('\r\n', 1, true) and '\r\n' or '\n'
        if contents ~= '' and contents:sub(-1) ~= '\n' then contents = contents .. newline end
        return contents .. value .. newline
    end)
    if not ok then message('Cannot save preset: ' .. tostring(err)); return end
    append_values(key, {value})
    new_tags[key]:set_text('')
    local problems = {}
    refresh_preset(key, problems)
    message('Preset saved and added to ' .. key .. '. Click Save changes to write video metadata.' ..
        (#problems > 0 and '\n' .. table.concat(problems, '\n') or ''))
end
local function add_preset(key)
    if pending and pending.mode == 'read' then message('Check the load operation first.'); return end
    if clears[key]:get_checked() then message('Uncheck Clear on Save before adding values.'); return end
    if legacy[key] and fields[key]:get_text() == baseline[key] then
        message('This field has existing values containing whitespace. Type a replacement first.'); return
    end
    local selection = presets[key].widget:get_selection()
    local selected = {}
    for index, value in ipairs(presets[key].values) do
        if selection[index + 1] then table.insert(selected, value) end
    end
    if #selected == 0 then return end
    append_values(key, selected)
end
function save()
    if pending then message('An operation is running. Click Check status.'); return end
    if not current then message(load_error or 'Load current video and Check status first.'); return end
    local request = {file=current.path, fingerprint=current.fingerprint, mode='save'}
    for _, key in ipairs(names) do
        local value = fields[key]:get_text()
        if clears[key]:get_checked() then
            request['clear_' .. key] = 'true'
        elseif value ~= baseline[key] then
            if not whitespace(value):find('%S') then message('Use Clear on Save to remove an entire field.'); return end
            request[key] = value
        end
    end
    request.append_genre_to_album = append_genre:get_checked() and 'true' or 'false'
    local ok, err = save_album_setting(request.append_genre_to_album)
    if not ok then message('Cannot save option: ' .. tostring(err)); return end
    -- Retain the input item before stop destroys the active input. Never use
    -- the new current item when the asynchronous save completes.
    local cache_item = vlc.input.item()
    if cache_item and local_path(cache_item:uri()) ~= current.path then cache_item = nil end
    cache_item = cache_item or current.cache_item
    if local_path(target_uri()) == current.path then
        trace('stop playback')
        vlc.playlist.stop()
        trace('playback stop returned')
    end
    launch(request, cache_item)
end
function remove_backups()
    if pending then message('An operation is running. Click Check status.'); return end
    if not current or local_path(target_uri()) ~= current.path then
        message('Load the selected video and Check status before removing backups.'); return
    end
    launch({file=current.path, mode='backups_preview'})
end
function confirm_remove_backups()
    if pending then message('An operation is running. Click Check status.'); return end
    if not backup_review or not current or current.path ~= backup_review.path or
            local_path(target_uri()) ~= backup_review.path then
        backup_review = nil
        message('Click Remove backups and Check status to review this video first.'); return
    end
    launch({file=backup_review.path, mode='backups_delete', backup_token=backup_review.token})
end
function cancel_remove_backups()
    backup_review = nil
    if pending and pending.mode == 'backups_preview' then pending.cancelled = true end
    if pending and pending.mode == 'backups_delete' then
        message('Removal already submitted. Click Check status for the result.')
    else
        message('Backup confirmation cancelled.')
    end
end
function check_status(follow_navigation)
    if not pending then message(load_error or 'No operation pending.'); return end
    -- A queued input event may not have run yet when this button is clicked.
    if pending.mode == 'read' and local_path(target_uri()) ~= pending.path then
        load_current()
        return
    end
    local file = io.open(pending.job .. '/result.txt', 'rb')
    if not file then message('Still working. Check again shortly. Log: ' .. pending.job .. '/worker.log'); return end
    local result = {}
    for line in file:lines() do
        local key, value = line:match('^([^=]+)=(.*)$')
        if key then result[key] = decode(value) end
    end
    file:close()
    local done = pending
    pending = nil
    if result.state ~= 'success' then
        local problem = (result.message or 'Invalid helper result.') .. '\nLog: ' .. done.job .. '/worker.log'
        if done.mode == 'read' then load_failed(problem) else message(problem) end
        return
    end
    if done.mode == 'backups_preview' or done.mode == 'backups_delete' then
        if done.mode == 'backups_preview' then
            if done.cancelled or not current or current.path ~= done.path or local_path(target_uri()) ~= done.path then
                message('Video changed. Backup confirmation cancelled.')
            elseif tonumber(result.backup_count) == 0 then
                message('No backup files found for this video.')
            else
                backup_review = {path=done.path, token=result.backup_token}
                message('Remove ' .. result.backup_count .. ' backup files (' ..
                    string.format('%.1f MiB', tonumber(result.backup_bytes) / 1048576) ..
                    ') for:\n' .. done.path .. '\nPermanent deletion. Click Confirm removal or Cancel removal.')
            end
        else
            message(result.message or 'Backup removal completed.')
        end
        return
    end
    load_error = nil
    current = {path=result.file, fingerprint=result.fingerprint, cache_item=done.cache_item}
    filename:set_text(html(result.file))
    local warnings = {}
    if done.mode == 'save' and done.cache_item then
        trace('refresh VLC metadata')
        local ok, err = pcall(function()
            for _, key in ipairs(names) do
                done.cache_item:set_meta(key, result[key] or '')
            end
        end)
        trace('metadata refresh returned')
        if not ok then
            table.insert(warnings, 'File saved, but VLC display refresh failed: ' .. tostring(err))
        end
    end
    for _, key in ipairs(names) do
        baseline[key] = result[key] or ''
        legacy[key] = result[key .. '_legacy'] == '1'
        if done.mode == 'read' then
            fields[key]:set_text(baseline[key])
            clears[key]:set_checked(false)
        elseif clears[key]:get_checked() == done.clear_snapshot[key] then
            -- A checkbox changed during the save is a new pending edit, just
            -- like text changed while the worker was running.
            if fields[key]:get_text() == done.snapshot[key] then
                fields[key]:set_text(baseline[key])
            end
            clears[key]:set_checked(false)
        end
        if legacy[key] then table.insert(warnings, key .. ': existing value contains whitespace; preserved until you replace this field.') end
    end
    message((done.mode == 'read' and 'Loaded. Spaces separate values.' or result.message or
        'Saved and verified. Reopen the video to refresh VLC. Backup: ' .. (result.backup or '')) ..
        (#warnings > 0 and '\n' .. table.concat(warnings, '\n') or ''))
    -- Finish the old save before loading the latest playlist target.
    -- load_current's own status collection must not launch a second read.
    if follow_navigation ~= false and local_path(target_uri()) ~= done.path then
        load_current()
    end
end
function activate()
    dialog = vlc.dialog('Π Metadata Pro')
    dialog:add_label('<b>Metadata Pro</b> · Give your videos a little order<br>' ..
        '<small>Click <b>Load current video</b> to get started.<br>' ..
        'Unsure what is happening? Click <b>Check status</b> to see progress or results.</small><br>' ..
        '<small>In the main fields, spaces separate tags; underscores join words within a tag.</small>', 1, 1, 3, 1)
    dialog:add_label('<p align="right"><small>Version ' .. html(VERSION) ..
        '<br>Build date ' .. html(BUILD_DATE) .. '</small></p>', 4, 1, 2, 1)
    filename = dialog:add_label('No file loaded', 1, 2, 5, 1)
    local album_setting = load_settings()
    append_genre = dialog:add_check_box('Append sorted Genre values to Album on Save', album_setting, 1, 3, 3, 1)
    dialog:add_button('☰ Refresh presets', reload_presets, 4, 3, 2, 1)
    for index, key in ipairs(names) do
        local field = key
        local row = 4 + (index - 1) * (quick_tag_editing and 4 or 3)
        dialog:add_label('<b>' .. key:sub(1,1):upper() .. key:sub(2) .. '</b>', 1, row)
        fields[key] = dialog:add_text_input('', 2, row, 2, 1)
        clears[key] = dialog:add_check_box('Clear on Save', false, 4, row, 2, 1)
        presets[key] = {widget=dialog:add_list(2, row+1, 2, 1, 240, 65), values={}}
        dialog:add_button('+ Add selected', traced('add preset', function() add_preset(field) end), 4, row+1, 2, 1)
        if quick_tag_editing then
            dialog:add_label('<b>＋ New ' .. key .. '</b>', 1, row+2)
            new_tags[key] = dialog:add_text_input('', 2, row+2, 2, 1)
            dialog:add_button('Add ' .. key, traced('create preset', function() create_preset(field) end), 4, row+2, 2, 1)
        end
        local hint = quick_tag_editing and
            '<small>Use underscores instead of spaces: Pink_Floyd.</small><br>' or ''
        dialog:add_label(hint .. '<br><hr><br>', 1, row + (quick_tag_editing and 3 or 2), 5, 1)
    end
    local footer = quick_tag_editing and 16 or 13
    dialog:add_button('↓ Load current video', load_current, 1, footer, 2, 1)
    dialog:add_button('✓ Save changes', save, 3, footer, 2, 1)
    dialog:add_button('× Discard edits', discard_edits, 5, footer)
    dialog:add_button('↻ Check status', check_status, 1, footer+1, 5, 1)
    -- VLC's QTextBrowser ignores the requested height during layout. A label
    -- keeps messages compact while allowing longer errors to remain visible.
    status = dialog:add_label('', 1, footer+2, 5, 1)
    message('Spaces separate values. Save stops playback and keeps a backup.')
    dialog:add_button('Remove backups', remove_backups, 1, footer+3, 2, 1)
    dialog:add_button('Confirm removal', confirm_remove_backups, 3, footer+3, 2, 1)
    dialog:add_button('Cancel removal', cancel_remove_backups, 5, footer+3)
    reload_presets()
    load_current()
end
function menu()
    return {[1]='Show editor', [2]='Hide editor'}
end
function trigger_menu(id)
    if not dialog then return end
    if id == 1 then
        -- VLC 3 only changes visibility: this does not raise a covered window
        -- or restore a minimized one. Use Hide then Show for covered windows.
        dialog:show()
    elseif id == 2 then
        dialog:hide()
    end
end
function close()
    -- Closing discards UI-only edits. Submitted workers own their requests
    -- and finish independently; never keep the window trapped open.
    vlc.deactivate()
end
function deactivate()
    cancel_read()
    if dialog then
        trace('delete dialog')
        dialog:delete()
        trace('dialog deleted')
    end
    dialog, current, pending, load_error, backup_review = nil, nil, nil, nil, nil
    fields, presets, legacy, baseline = {}, {}, {}, {}
    clears, new_tags = {}, {}
    quick_tag_editing = false
end

-- Register wrappers before VLC invokes activate and creates its button callbacks.
-- Discovery runs without Lua's standard libraries; only runtime needs wrappers.
if ipairs and _G then
for _, name in ipairs({'activate', 'input_changed', 'load_current', 'save',
        'check_status', 'reload_presets', 'discard_edits', 'remove_backups',
        'confirm_remove_backups', 'cancel_remove_backups', 'trigger_menu', 'close', 'deactivate'}) do
    _G[name] = traced(name, _G[name])
end
end
