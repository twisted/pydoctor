// This file contains the code that drives the search system UX.
// It's included in every HTML file.
// Depends on library files searchlib.js and ajax.js (and of course lunr.js)

// Ideas for improvments: 
// - Include filtering buttons:
//    - search only in the current module
//    - have a query frontend that helps build complex queries
// - Filter out results that have score > 0.001 by default and show them on demand.
// - Should we change the default term presence to be MUST and not SHOULD ?
//        -> Hack something like 'name index -value' -> '+name +index -value'
//        ->      'name ?index -value' -> '+name index -value'
// - Highlight can use https://github.com/bep/docuapi/blob/5bfdc7d366ef2de58dc4e52106ad474d06410907/assets/js/helpers/highlight.js#L1
// Better: Add support for AND and OR with parenthesis, ajust this code https://stackoverflow.com/a/20374128

//////// GLOBAL VARS /////////

let input = document.getElementById('search-box');
let results_container = document.getElementById('search-results-container');
let results_list = document.getElementById('search-results'); 
let searchInDocstringsButton = document.getElementById('search-docstrings-button'); 
let searchInDocstringsCheckbox = document.getElementById('toggle-search-in-docstrings-checkbox');

// setTimeout variable to warn when a search takes too long
var _setLongSearchInfosTimeout = null;

//////// UI META INFORMATIONS FUNCTIONS /////////

function _setInfos(message, box_id, text_id) {
  document.getElementById(text_id).textContent = message;
  if (message.length>0){
    document.getElementById(box_id).style.display = 'block';
  }
  else{
    document.getElementById(box_id).style.display = 'none';
  }
}

/**
 * Set the search status.
 */
function setStatus(message) {
  document.getElementById('search-status').textContent = message;
}

/**
 * Show a warning, hide warning box if empty string.
 */
function setWarning(message) {
  _setInfos(message, 'search-warn-box', 'search-warn');
}

/**
 * Say that Something went wrong.
 */
function setErrorStatus() {
  resetLongSearchTimerInfo()
  setStatus("Something went wrong.");
  setErrorInfos();
}

/**
 * Show additional error infos (used to show query parser errors infos) or tell to go check the console.
 * @param message: (optional) string
 */
function setErrorInfos(message) {
  if (message != undefined){
    setWarning(message);
  }
  else{
    setWarning("Error: See development console for details.");
  }
}

/**
 * Reset the long search timer warning.
 */
function resetLongSearchTimerInfo(){
  if (_setLongSearchInfosTimeout){
    clearTimeout(_setLongSearchInfosTimeout);
  }
}

/**
 * Say that this search is taking longer than usual.
 */
function setLongSearchInfos(){
  setWarning("This is taking longer than usual... You can keep waiting for the search to complete, or retry the search with other terms.");
}

//////// UI SHOW/HIDE FUNCTIONS /////////

function hideResultContainer(){
  results_container.style.display = 'none';
  if (!document.body.classList.contains("search-help-hidden")){
    document.body.classList.add("search-help-hidden");
  }
}

function showResultContainer(){
  results_container.style.display = 'block';
}

function toggleSearchHelpText() {
  document.body.classList.toggle("search-help-hidden");
  if (document.body.classList.contains("search-help-hidden") && input.value.length==0){
    hideResultContainer();
  }
  else{
    showResultContainer();
  }
}

function resetResultList(){
  resetLongSearchTimerInfo();
  results_list.innerHTML = '';
}

function clearSearch(){
  hideResultContainer();
  resetResultList();
  setWarning('');
  setStatus('');

  input.value = '';
  updateClearSearchBtn();
}

/**
 * Show and hide the (X) button depending on the current search input.
 * We do not show the (X) button when there is no search going on.
 */
 function updateClearSearchBtn(){
  
  if (input.value.length>0){
    document.getElementById('search-clear-button').style.display = 'inline-block';
  }
  else{
    document.getElementById('search-clear-button').style.display = 'none';
  }
}

//////// SEARCH WARPPER FUNCTIONS /////////

var _lastSearchStartTime = null;
var _lastSearchInput = null;
/** 
 * Do the actual searching business
 */
function search(){
  let _searchStartTime = performance.now();

  // Get the query terms 
  let _query = input.value;

  // In chrome, two events are triggered simultaneously for the input event.
  // So we discard consecutive (within the same 0.001s) requests that have the same search query.
  if ((
    (_searchStartTime-_lastSearchStartTime) < (0.001*1000)
    ) && (_query === _lastSearchInput) ){
      return;
  }

  setTimeout(() =>{
    setWarning('');
    showResultContainer();
    setStatus("Searching...");
  }, 0);

  // Setup query meta infos.
  _lastSearchStartTime = _searchStartTime
  _lastSearchInput = _query;

  if (!_query.length>0){
    resetResultList();
    setStatus('');
    hideResultContainer();
    // Special case: we need to terminate the worker manualy if user deleted everything is the saerch box
    terminateSearchWorker();
    return;
  }

  console.log("Your query is: "+ _query)

  if (!window.Worker) {
    setStatus("Cannot search: JavaScript Worker API is not supported in your browser. ");
    return;
  }

  resetResultList();

  // Determine indexURL
  let indexURL = _isSearchInDocstringsEnabled() ? "fullsearchindex.json" : "searchindex.json";
  
  // If search in docstring is enabled: 
  //  -> customize query function to include docstring for clauses applicable for all fields
  let _fields = _isSearchInDocstringsEnabled() ? ["name", "names", "qname", "docstring"] : ["name", "names", "qname"];

  // After 4 seconds of searching, warn that this is taking more time than usual.
  _setLongSearchInfosTimeout = setTimeout(setLongSearchInfos, 4000);

  // Search 
  lunrSearch(_query, indexURL, _fields, "lunr.js").then((lunrResults) => { 

      // outdated query results
      if (_searchStartTime != _lastSearchStartTime){return;}
      
      if (!lunrResults){
        setErrorStatus();
        throw("No data to show");
      }

      if (lunrResults.length == 0){
        setStatus('No results matches "' + _query + '"');
        resetLongSearchTimerInfo();
        return;
      }

      setStatus("One sec...");

      // Get result data
      return fetchResultsData(lunrResults, "all-documents.html").then((documentResults) => {

        // outdated query results
        if (_searchStartTime != _lastSearchStartTime){return;}

        // Edit DOM
        resetLongSearchTimerInfo();
        displaySearchResults(_query, documentResults, lunrResults)
        
        // Log stats
        console.log('Search for "' + _query + '" took ' + 
          ((performance.now() - _searchStartTime)/1000).toString() + ' seconds.')

        // End
      });

  }).catch((err) => {
    console.dir(err);
    setStatus('')
    if (err.message){
      resetLongSearchTimerInfo();
      setWarning(err.message) // Here we show the error because it's likely a query parser error.
    }
    else{
      setErrorStatus();
    }
    
  }); // lunrResults promise resolved

} // end search() function

/**
 * Given the query string, documentResults and lunrResults as used in search(), 
 * edit the DOM to add them in the search results list.
 */
function displaySearchResults(_query, documentResults, lunrResults){
  resetResultList();
  documentResults.forEach((dobj) => {
    results_list.appendChild(buildSearchResult(dobj));
  });

  if (lunrResults[0].score <= 5){
    if (lunrResults.length > 500){
      setWarning("Your search yielded a lot of results! and there aren't many great matches. Maybe try with other terms?");
    }
    else{
      setWarning("Unfortunately, it looks like there aren't many great matches for your search. Maybe try with other terms?");
    }
  }
  else {
    if (lunrResults.length > 500){
      setWarning("Your search yielded a lot of results! Maybe try with other terms?");
    }
    else{
      setWarning('');
    }
  }

  let publicResults = documentResults.filter(function(value){
    return !value.querySelector('.privacy').innerHTML.includes("PRIVATE");
  })

  if (publicResults.length==0){
    setStatus('No results matches "' + _query + '". Some private objects matches your search though.');
  }
  else{
    setStatus(
      'Search for "' + _query + '" yielded ' + publicResults.length + ' ' +
      (publicResults.length === 1 ? 'result' : 'results') + '.');
  }
}

/** 
 * Main entrypoint to [re]launch the search.
 * Called everytime the search bar is edited.
*/
function launchSearch(){
  search();
}

function _isSearchInDocstringsEnabled() {
  return searchInDocstringsCheckbox.checked;
}

function toggleSearchInDocstrings() {
  if (searchInDocstringsCheckbox.checked){
    searchInDocstringsButton.classList.add('label-success')
  }
  else{
    if (searchInDocstringsButton.classList.contains('label-success')){
      searchInDocstringsButton.classList.remove('label-success')
    }
  }
  if (input.value.length>0){
    launchSearch()
  }
}

////// SETUP //////

// Attach launchSearch() to search text field update events.

input.oninput = (event) => {
  launchSearch();
};
input.onkeyup = (event) => {
  if (event.key === 'Enter') {
    launchSearch();
  }
};
input.onfocus = (event) => {
  // Load fullsearchindex.json, searchindex.json and all-documents.html to have them in the cache asap.
  httpGet("all-documents.html", ()=>{}, ()=>{});
  httpGet("searchindex.json", ()=>{}, ()=>{});
  httpGet("fullsearchindex.json", ()=>{}, ()=>{});
  httpGet("lunr.js", ()=>{}, ()=>{});
}

// Close the dropdown if the user clicks on echap key
document.onkeyup = function(evt) {
  evt = evt || window.event;
  if (evt.key === "Escape" || evt.key === "Esc") {
      hideResultContainer();
  }
};

// Init search and help text. 
// search box is not visible by default because
// we don't want to show it if the browser do not support JS.
window.addEventListener('load', (event) => {
  document.getElementById('search-box-container').style.display = 'block';
  document.getElementById('search-help-box').style.display = 'block';
  hideResultContainer();
});

// Hide the dropdown if the user clicks outside of it
window.addEventListener("click", function(event) {
  if (event){
      if (!event.target.closest('#search-results-container') 
          && !event.target.closest('#search-box')
          && !event.target.closest('#search-help-button')){
            hideResultContainer();
            return;
      }
      if (event.target.closest('#search-box')){
        if (input.value.length>0){
          showResultContainer();
        }
      }
  }
});