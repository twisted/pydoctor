// Cookie manipulation functions, from https://www.w3schools.com/js/js_cookies.asp

function setCookie(cname, cvalue, exdays) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
    var expires = "expires="+d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}
  
function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
        c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
        return c.substring(name.length, c.length);
        }
    }
    return "";
}

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
    document.querySelector('#showPrivate button').innerText =
        hidden ? 'Show Private API' : 'Hide Private API';
    if (history) {
        var search = hidden ? document.location.pathname : '?private=1';
        history.replaceState(null, '', search + document.location.hash);
    }
}

initPrivate();

// Toogle sidebar collapse

function initSideBarCollapse() {
    var collapsed = getCookie("pydoctor-sidebar-collapsed");
    if (collapsed == "yes") {
        document.body.classList.add("sidebar-collapsed");
    }
    if (collapsed == ""){
        setCookie("pydoctor-sidebar-collapsed", "no", 365);
    }
    updateSideBarCollapse();
    document.querySelector('.sidebarcontainer').style.display = 'flex'; 
}

function toggleSideBarCollapse() {
    if (document.body.classList.contains('sidebar-collapsed')){
        document.body.classList.remove('sidebar-collapsed');
        setCookie("pydoctor-sidebar-collapsed", "no", 365);
    }
    else {
        document.body.classList.add("sidebar-collapsed");
        setCookie("pydoctor-sidebar-collapsed", "yes", 365);
    }
    
    updateSideBarCollapse();
}

function updateSideBarCollapse() {
    var collapsed = document.body.classList.contains('sidebar-collapsed');
    document.querySelector('#collapseSideBar a').innerText = collapsed ? '»' : '«';
    // Fixes renderring issue with safari. 
    // https://stackoverflow.com/a/8840703
    var sidebarcontainer = document.querySelector('.sidebarcontainer');
    sidebarcontainer.style.display='none';
    sidebarcontainer.offsetHeight; // no need to store this anywhere, the reference is enough
    sidebarcontainer.style.display='flex';
}

initSideBarCollapse();
