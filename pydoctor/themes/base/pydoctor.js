// Toogle private view

function initPrivate() {
    var params = (new URL(document.location)).searchParams;
    if (!params || !parseInt(params.get('private'))) {
        var show = false;
        var hash = document.location.hash;
        
        if (hash != '') {
            var anchor = document.querySelector('a[name="' + hash.substring(1) + '"]');
            show = anchor && anchor.parentNode.classList.contains('private');
        }

        if (!show) {
            document.body.classList.add("private-hidden");
        }
    }
    updatePrivate();
}

function togglePrivate() {
    document.body.classList.toggle("private-hidden");
    updatePrivate();
}
function updatePrivate() {
    var hidden = document.body.classList.contains('private-hidden');
    document.querySelector('#show-private button').innerText =
        hidden ? 'Show Private API' : 'Hide Private API';
    if (history) {
        var search = hidden ? document.location.pathname : '?private=1';
        history.replaceState(null, '', search + document.location.hash);
    }
}

initPrivate();

// Toggle doctest output visibility

function initDoctest() {
    // Add click handlers to all doctest toggle buttons
    var buttons = document.querySelectorAll('button.doctest-toggle');
    buttons.forEach(function(button) {
        button.addEventListener('click', function() {
            var container = button.closest('div.doctest-output');
            if (container) {
                container.classList.toggle('hide-output');
            }
        });
    });
}

initDoctest()
