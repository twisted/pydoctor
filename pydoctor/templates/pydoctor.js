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
    document.querySelector('#showPrivate button').innerText =
        hidden ? 'Show Private API' : 'Hide Private API';
    if (history) {
        // Ensure that search paramaters do not get overriden by private=1
        var search_params = (new URL(document.URL)).searchParams;
        
        var new_location = document.location.pathname;

        if (!hidden){
            new_location = new_location + '?private=1';
        }
        else{
            if (search_params.has('private')){
                search_params.delete('private');
            }
        }

        if (search_params.toString().length>0){
            if (hidden){
                new_location = new_location + '?';
            }
            else{
                new_location = new_location + '&';
            }
            new_location = new_location + search_params;
        }

        history.replaceState(null, '', new_location + document.location.hash);
    }
}
initPrivate();
