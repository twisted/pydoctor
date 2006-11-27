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
