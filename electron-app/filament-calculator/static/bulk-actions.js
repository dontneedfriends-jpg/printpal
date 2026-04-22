function baToggleSelectMode(opts) {
    var btn = document.getElementById(opts.btnId);
    var bulkActions = document.getElementById(opts.bulkId);
    var checkboxes = document.querySelectorAll('.' + opts.checkClass);
    var selectCols = document.querySelectorAll('.' + (opts.selectColClass || 'select-col'));

    if (bulkActions.style.display === 'none') {
        bulkActions.style.display = 'block';
        if (btn) btn.textContent = '\u2611 ' + (opts.selectText || 'Select');
        checkboxes.forEach(function(cb) { cb.parentElement.style.display = ''; });
        selectCols.forEach(function(el) { el.style.display = ''; });
    } else {
        bulkActions.style.display = 'none';
        if (btn) btn.textContent = '\u2610 ' + (opts.selectText || 'Select');
        checkboxes.forEach(function(cb) { cb.checked = false; cb.parentElement.style.display = 'none'; });
        selectCols.forEach(function(el) { el.style.display = 'none'; });
        baUpdateSelectedCount(opts.checkClass, opts.countId, opts.selectedText);
    }
}

function baToggleAll(checkClass) {
    var checkboxes = document.querySelectorAll('.' + checkClass);
    var allChecked = Array.from(checkboxes).every(function(cb) { return cb.checked; });
    checkboxes.forEach(function(cb) { cb.checked = !allChecked; });
    baUpdateSelectedCount(checkClass);
}

function baUpdateSelectedCount(checkClass, countId, selectedText) {
    var checked = document.querySelectorAll('.' + checkClass + ':checked');
    if (countId) {
        var label = document.getElementById(countId);
        if (label) label.textContent = checked.length + ' ' + (selectedText || 'selected');
    }
    return checked;
}

function baBulkDelete(opts) {
    var checked = baUpdateSelectedCount(opts.checkClass, opts.countId, opts.selectedText);
    if (checked.length === 0) return;

    appConfirm(checked.length + ' ' + opts.confirmText).then(function(ok) {
        if (!ok) return;
        var ids = Array.from(checked).map(function(cb) { return cb.value; });
        var promises = ids.map(function(id) {
            return fetch(opts.deleteUrl.replace('{id}', id), { method: 'POST' })
                .then(function(resp) { return resp.json(); });
        });

        Promise.all(promises).then(function(results) {
            checked.forEach(function(cb) {
                var row;
                if (opts.rowIdPrefix) {
                    row = document.getElementById(opts.rowIdPrefix + cb.value);
                } else if (opts.rowSelector) {
                    row = document.querySelector(opts.rowSelector.replace('{id}', cb.value));
                }
                if (row) row.remove();
                if (opts.onDelete) opts.onDelete(cb.value, results);
            });
            showToast(checked.length + ' ' + opts.deletedText, 'success');
            baUpdateSelectedCount(opts.checkClass, opts.countId, opts.selectedText);
            baToggleSelectMode(opts);
        });
    });
}
