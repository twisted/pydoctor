function setStatus(message) {
  document.getElementById('search-status').textContent = message;
}

function _setInfos(message, box_id, text_id) {
  document.getElementById(text_id).textContent = message;
  if (message.length>0){
    document.getElementById(box_id).style.display = 'block';
  }
  else{
    document.getElementById(box_id).style.display = 'none';
  }
}

function setPrivateInfos(message) {
  _setInfos(message, 'search-private-infos-box', 'search-private-infos');
}

function setInfos(message) {
  _setInfos(message, 'search-infos-box', 'search-infos');
}

function setWarning(message) {
  _setInfos(message, 'search-warn-box', 'search-warn');
}

function setErrorStatus() {
  setStatus("Something went wrong.");
}

function setErrorInfos(message) {
  if (message != undefined){
    setWarning("Error: " +  message + ". See development console for details.");
  }
  else{
    setWarning("Error: See development console for details.");
  }
}

function buildSearchResult(dobj) {

  // Build one result item
  var li = document.createElement('li'),
      article = document.createElement('article'),
      header = document.createElement('header'),
      section = document.createElement('section'),
      code = document.createElement('code'),
      a = document.createElement('a'),
      p = document.createElement('p');

  p.innerHTML = dobj.querySelector('.summary').innerHTML;
  a.setAttribute('href', dobj.querySelector('.url').innerHTML);
  a.textContent = dobj.querySelector('.fullName').innerHTML;
  
  let kind_value = dobj.querySelector('.kind').innerHTML;
  let type_value = dobj.querySelector('.type').innerHTML;

  // Adding '()' on functions and methods
  if (type_value.endsWith("Function")){
      a.textContent = a.textContent + '()';
  }
  
  // Putting everything together
  li.appendChild(article);
  article.appendChild(header);
  article.appendChild(section);
  header.appendChild(code);
  code.appendChild(a);
  section.appendChild(p);

  // Set private and kind as the CSS class
  let ob_css_class = dobj.querySelector('.kind').innerHTML.toLowerCase().replace(' ', '');
  if (dobj.querySelector('.privacy').innerHTML.includes('PRIVATE')){
    li.setAttribute('class', 'private ' + ob_css_class);
  }
  else{
    li.setAttribute('class', ob_css_class)
  }

  //Add type metadata in order to be able to filter
  let type_metadata = document.createElement('meta');
  type_metadata.setAttribute('name', 'type');
  type_metadata.setAttribute('class', 'type');
  type_metadata.setAttribute('content', type_value);
  li.appendChild(type_metadata);

  //Add kind metadata in order to be able to filter
  let kind_metadata = document.createElement('meta');
  kind_metadata.setAttribute('name', 'kind');
  kind_metadata.setAttribute('class', 'kind');
  kind_metadata.setAttribute('content', kind_value);
  li.appendChild(kind_metadata);

  return li;
}

function setLongSearchInfos(){
  setWarning("This is taking longer than usual... You can keep waiting for the search to complete, or retry the search with other terms.");
}

function buildInfosString(search_results_documents, priv){

  let nb_classes = search_results_documents.filter(function(value){
    return (value.querySelector('.kind').innerHTML.endsWith("Class") && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE")));
  }).length;  

  let nb_interfaces = search_results_documents.filter(function(value){
    return (value.querySelector('.kind').innerHTML.endsWith("Interface") && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE")));
  }).length;  

  let nb_methods = search_results_documents.filter(function(value){
    return (value.querySelector('.kind').innerHTML.endsWith("Method") && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE")));
  }).length;  

  let nb_functions = search_results_documents.filter(function(value){
    return (value.querySelector('.kind').innerHTML.endsWith("Function") && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE")));
  }).length;  

  let nb_modules = search_results_documents.filter(function(value){
    return (value.querySelector('.kind').innerHTML.endsWith("Module") || value.querySelector('.kind').innerHTML.endsWith("Package")) && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE"));
  }).length;  
  
  // We don't go in the details of property/attribute/instance variable. 
  let nb_var = search_results_documents.filter(function(value){
    return (value.querySelector('.type').innerHTML.endsWith("Attribute")) && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE"));

  }).length; 

  var infoStr = 'Including ' + 
    (nb_modules>0 ? (nb_modules.toString() + (priv ? " private" : "")+ ' module'+(nb_modules>=2? 's' : '')+', ') : '')
    + 
    (nb_interfaces>0 ? (nb_interfaces.toString() + (priv ? " private" : "") + ' interface'+(nb_interfaces>=2 ? 'es' : '')+', ') : '')
    + 
    (nb_classes>0 ? (nb_classes.toString() + (priv ? " private" : "") + ' class'+(nb_classes>=2 ? 'es' : '')+', ') : '')
    + 
    (nb_methods>0 ? (nb_methods.toString() + (priv ? " private" : "")+ ' method'+(nb_methods>=2? 's' : '')+', ') : '')
    +
    (nb_functions>0 ? (nb_functions.toString() + (priv ? " private" : "")+ ' function'+(nb_functions>=2? 's' : '') + ', ' ) : '')
    + 
    (nb_var>0 ? (nb_var.toString() + (priv ? " private" : "") + ' variable'+(nb_var>=2? 's' : '')+', ') : '') ;

  // Dirty replacing of the commas so the output is a phrase that finishes by ' and xx things.',
  // which is more readable than commas everywhere.
  var pos = infoStr.lastIndexOf(',');
  var commas_count = (infoStr.match(/,/g) || []).length;
  var infoStrPart1 = infoStr.substring(0,pos);
  let infoStrPart2Init = infoStr.substring(pos+1);
  var infoStrPart2 = infoStr.substring(pos+1);

  if (infoStrPart2Init.trim().length==0){ 
    infoStrPart2 = '.'; }
  else{ 
    infoStrPart2 = ' and' + infoStrPart2; }
  if (commas_count>1 && infoStrPart2Init.trim().length == 0){
    var pos2 = infoStrPart1.lastIndexOf(',');
    infoStrPart1 = infoStrPart1.substring(0,pos2) + ' and' + infoStrPart1.substring(pos2+1); }
  return(infoStrPart1 + infoStrPart2);
}

///////////////////// FILTER //////////////////////////

// Close the dropdown if the user clicks outside of it
window.addEventListener("click", function(event) {
  let dropdown_input = document.getElementById("search-filter-dropdown-input")
  if (event && !event.target.matches('#search-filter-dropdown-input') && dropdown_input.checked == true) {
    setTimeout(function(){
      dropdown_input.checked = false;
    }, 1);
  }
});

function filterItems(types, label, dropdown_item_pressed){

  console.log("Filtering search results: " + label);

  let results_list = Array.prototype.slice.call(document.getElementById('search-results').childNodes); 
  
  var match_items = [];

  results_list.forEach(function(li){
    var match = false;
    
    types.forEach(function(type){
      // We don't go in the details of property/attribute/instance variable.
      // So the when requesting to filter on 'Attribute', this is a special case.
      let selector = type === 'Attribute' ? '.type' : '.kind';
      if (li.querySelector(selector).getAttribute('content').endsWith(type)){
        match = true;
      }
    })

    if (match){
      li.style.display = "block";
      match_items.push(li);
    }
    else{
      li.style.display = "none";
    }
  })

  if (label.length>0){
    document.getElementById("search-filter-button").querySelector(".button-label").textContent = 'Filter: ' + label;
  }

  // Reset filter dropdown
  initFilterDropdown(results_list);
  document.getElementById("search-filter-show-all").style.display = 'block';
  document.getElementById("search-filter-button").classList.add("active")

  dropdown_item_pressed.style.display = 'none';

  console.log(match_items.length.toString() + " items matches the filter");
  console.log(match_items);

}

function showAllItems(){
  filterItems(['Class', 'Interface', 'Function', 'Method', 'Module', 'Package', 'Attribute'], 'Choose...', document.getElementById("search-filter-show-all"))
  document.getElementById("search-filter-button").classList.remove("active")
}

function _initSearchFilter(results_list, input, types){

  let nb_things = results_list.filter(function(value){
    var match = false;
    types.forEach(function(type){
      
      // We don't go in the details of property/attribute/instance variable
      let selector = type === 'Attribute' ? '.type' : '.kind';
      var _type = value.querySelector(selector).getAttribute('content')
      
      if (!_type){
        // Filter on innerHTML if 'content' attr meta tags is undefined
        // This is needed because initFilterDropdown() is both called on 
        // the list of results build by buildSearchResult() with the kind/type data as meta tags
        // and also on the the original data present on all-documents.html for initialisation, 
        // where the data is stored in the innerHTML. 
        _type = value.querySelector(selector).innerHTML;
      }

      if(_type.endsWith(type)){
        match = true;
      }
    })
    
    return match;
  
  }).length;  

  if (nb_things==0){
    input.style.display = "none";
  }
  else{
    input.style.display = "block";
  }
}

function initFilterDropdown(results_list_p){

  let results_list = Array.prototype.slice.call(results_list_p);

  document.getElementById("search-filter-show-all").style.display = "none";

  _initSearchFilter(results_list, document.getElementById("search-filter-show-interfaces"), ["Interface"]);
  _initSearchFilter(results_list, document.getElementById("search-filter-show-classes"), ["Class"]);
  _initSearchFilter(results_list, document.getElementById("search-filter-show-functions"), ["Function"]);
  _initSearchFilter(results_list, document.getElementById("search-filter-show-methods"), ["Method"]);
  _initSearchFilter(results_list, document.getElementById("search-filter-show-modules"), ["Module", "Package"]);
  _initSearchFilter(results_list, document.getElementById("search-filter-show-attributes"), ["Attribute"]);
}

///////////////////// SEARCH //////////////////////////

function search(){

  let _url = new URL(document.URL);
  console.log(_url);

  var _setLongSearchInfosTimeout = null;
  var _query = null;

  // Get the query terms
  if (!_url.searchParams.has('search-query')){
    setStatus('No search query provided.')
    return ;
  }

  _query = _url.searchParams.get('search-query');

  if (!_query.length>0){
    setStatus('No search query provided.')
    return ;
  }

  // Set the search box text to the query terms
  document.getElementById('search-box').value = _query;

  console.log("Your query is: "+ _query)

  if (!window.Worker) {
    setStatus("Cannot search: JavaScript Worker API is not supported in your browser. ");
    return ;
  }

  let results_list = document.getElementById('search-results'); 

  setStatus("Searching...")

  // Setup the search worker   
  let worker = new Worker('search-worker.js');

  worker.postMessage({
    query: _query,
  });
  
  worker.onmessage = function (response) {

    if (_setLongSearchInfosTimeout){
      clearTimeout(_setLongSearchInfosTimeout)
    }
    setInfos('')
    setWarning('')
    
    console.log("Message received from worker: ")
    console.dir(response.data)

    if (!response.data.results){
      setErrorStatus();
      throw("No data received from worker")
    }

    if (response.data.results.length == 0){
      setStatus('No results matches "' + _query + '"');
      return ;
    }
    else{
      setStatus('Fetching documents...');
    }

    // Get result data
    httpGet("all-documents.html", function(response2) {
      let parser = new self.DOMParser();
      let all_documents = parser.parseFromString(response2, "text/html");
      let search_results_documents = [];
      
      response.data.results.forEach(function (result) {
          // Find the result model 
          var dobj = all_documents.getElementById(result.ref);
          
          if (!dobj){
              setErrorStatus();
              throw ("Cannot find document ID: " + result.ref)
          }
          // Save
          search_results_documents.push(dobj);

          // Display results: edit DOM
          let li = buildSearchResult(dobj);
          results_list.appendChild(li);

      });

      if (response.data.results[0].score <= 7){
        if (response.data.results.length > 500){
          setWarning("Your search yielded a lot of results! and there aren't many great matches. Maybe try with other terms?");
        }
        else{
          setWarning("Unfortunately, it looks like there aren't many great matches for your search. Maybe try with other terms?");
        }
      }
      else {
        if (response.data.results.length > 500){
          setWarning("Your search yielded a lot of results! Maybe try with other terms?");
        }
      }

      let public_search_results = search_results_documents.filter(function(value){
        return !value.querySelector('.privacy').innerHTML.includes("PRIVATE");
      })

      let private_search_results = search_results_documents.filter(function(value){
        return value.querySelector('.privacy').innerHTML.includes("PRIVATE");
      })

      if (public_search_results.length==0){
        setStatus('No results matches "' + _query + '"');
        setInfos('Some private objects matches your search though.');
      }
      else{

        setStatus(
          'Search for "' + _query + '" yielded ' + public_search_results.length + ' ' +
          (public_search_results.length === 1 ? 'result' : 'results') + '.');

        // Build complementary information string

        setInfos(buildInfosString(search_results_documents, false));
      }

      // Build PRIVATE complementary information string
      if (private_search_results.length > 0){
        setPrivateInfos(buildInfosString(search_results_documents, true));
      }
      else{
        // Hide the cell
        setPrivateInfos('')
      }
      

      initFilterDropdown(search_results_documents)

    },
    function(error){
      console.log(error);
      setErrorStatus();
      setErrorInfos(error.message);
  });

  };

  worker.onerror = function(error) {
    console.log(error);
    if (_setLongSearchInfosTimeout){
      clearTimeout(_setLongSearchInfosTimeout)
    }
    error.preventDefault();
    setErrorStatus();
    setErrorInfos(error.message);
  }


  _setLongSearchInfosTimeout = setTimeout(setLongSearchInfos, 8000);
}

try{
  search()
}
catch (err){
  console.log(err);
  setErrorStatus();
  setErrorInfos(err.message);
}
