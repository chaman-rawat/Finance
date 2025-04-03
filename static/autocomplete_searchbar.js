// Get element id's
const search = document.getElementById('search');
const matchList = document.getElementById('match-list');

// Search stock
const searchSymbol = async searchText => {
    if (searchText.length === 0) {
        matchList.innerHTML = '';
        return;
    }
    const res = await fetch(`https://ticker-2e1ica8b9.now.sh/keyword/${searchText}`);
    const stocks = await res.json();
    outputHtml(stocks);
};

// Show results in HtML
const outputHtml = matches => {
    if (matches.length > 0) {
        const html = matches
            .map(
                match => `<option value = "${match.symbol}">`
            )
            .join('');

        matchList.innerHTML = html;
    }
};

// defounce function defination
function debounce(func, timeout = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => {
            func(args);
        }, timeout);
    };
}

// wait for 350ms before calling function
const deboucedSearchSymbol = debounce(searchSymbol, 350);

// listen to input event
search.addEventListener('input', (event) => {
    console.log('called listerner')
    if (event.data !== undefined) {
        console.log('called ineer')
        deboucedSearchSymbol(search.value)
    }
});