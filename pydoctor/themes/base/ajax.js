function httpGet(url, onload, onerror) {   

    var xobj = new XMLHttpRequest();
    xobj.open('GET', url, true); // Asynchronous
    
    xobj.onload = function () {
        onload(xobj.responseText);
    };

    xobj.onerror = function (error) {
        console.log(error)
        onerror(error)
    };

    xobj.send(null);  
}
