function showBig ()
{
	document.getElementById("splitTables").style.display = "none";
	document.getElementById("bigTable").style.display = "block";

	document.getElementById("showSplitLink").style.display = "inline";
	document.getElementById("showBigLink").style.display = "none";
}

function showSplit ()
{
	document.getElementById("splitTables").style.display = "block";
	document.getElementById("bigTable").style.display = "none";

	document.getElementById("showSplitLink").style.display = "none";
	document.getElementById("showBigLink").style.display = "inline";
}

function hideId (id)
{
	var part;
	part = document.getElementById(id);
	if (part) part.style.display = 'none'
}

function showId (id)
{
	var part;
	part = document.getElementById(id);
	if (part) part.style.display = 'inline'
}

function hideAndShow(id)
{
	hideId(id + 'Link'); showId(id);
}

window.onload = function ()
{
	var spans,i;
	spans=document.getElementsByTagName('span');
	for(i = 0; i<spans.length;i++) {
		if (/hideIfJS/.test(spans[i].className)) {
			spans[i].style.display='none';
		}
		if (/showIfJS/.test(spans[i].className)) {
			spans[i].style.display='inline';
		}
	}
	showId('showBigLink');
}
