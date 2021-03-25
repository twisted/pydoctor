'use strict';

function setStatus(message) {
    document.getElementById('search-status').textContent = message;
}

async function buildIndex() {
    return lunr(function () {
        this.ref('i');
        this.field('name', {boost: 10});
        this.field('fullName', {boost: 5});
        this.field('docstring', {boost: 2});
        this.metadataWhitelist = ['position'];
        INDEX.forEach((doc, i) => {
            doc['i'] = i;
            this.add(doc);
        }, this);
    });
}

var buildSearchResult = function (result) {
    // Find the result model 
    const dobj = INDEX[parseInt(result.ref)];

    var li = document.createElement('li'),
        article = document.createElement('article'),
        header = document.createElement('header'),
        section = document.createElement('section'),
        code = document.createElement('code'),
        a = document.createElement('a'),
        p = document.createElement('p')

    p.textContent = dobj.docstring;

    a.setAttribute('href', dobj.url);
    a.textContent = dobj.fullName + (dobj.kind == 'Function' ? '()' : '');

    li.appendChild(article);
    article.appendChild(header);
    article.appendChild(section);
    header.appendChild(code);
    code.appendChild(a);
    section.appendChild(p);

    return li
  }

function search(query) {
    
    _search(query).catch(err => {
        if (err instanceof lunr.QueryParseError) {
            setStatus(e.message);
            return;
          } else {
            setStatus("Something went wrong. See development console for details.");
            throw err;
          }
    });
}

async function _search(query) {
    if (!query) {
        setStatus('No query provided.');
        return;
    }

    // Call lunr.Index.search
    const results = (await lunr_index).search(query);
    if (!results.length) {
        setStatus('No results matches "' + query + '"');
        return;
    }
    
    setStatus(
        'Search for "' + query + '" yielded ' + results.length + ' ' +
        (results.length === 1 ? 'result' : 'results') + ':');
    
    results.forEach(function (result) {
        document.getElementById('search-results').appendChild(buildSearchResult(result));
    });
}

setStatus("Searching...");


// Build the index
const lunr_index = buildIndex();

// Launch the search
const _query = decodeURIComponent(new URL(window.location).hash.substring(1))
document.getElementById('search-box').value = _query
search(_query);
