function render_quote_tag_button(tag) {
    let quote_tag_button = document.createElement("button");
    quote_tag_button.className = "btn btn-info px-2 py-1 quote_tag";
    quote_tag_button.textContent = tag;
    return quote_tag_button;
}

function render_quote_tag_edit_input(tag) {
    let quote_tag_edit_input = document.createElement("input");
    quote_tag_edit_input.className = "form-control quote_input";
    quote_tag_edit_input.setAttribute("type", "text");
    quote_tag_edit_input.value = tag;
    return quote_tag_edit_input;
}

function append_quote_tag_new_input(before) {
    before.before(render_quote_tag_new_input(before));
}

function render_quote_tag_new_input(before) {
    let quote_tag_edit_input_new = document.createElement("input");
    quote_tag_edit_input_new.className = "form-control quote_input_new_fresh";
    quote_tag_edit_input_new.setAttribute("type", "text");
    quote_tag_edit_input_new.setAttribute("placeholder", "Tag");
    quote_tag_edit_input_new.addEventListener("input", (event) => {
        let edit_input = event.target;
        if (edit_input.className.includes("quote_input_new_fresh")) {
            edit_input.className = edit_input.className.replace("quote_input_new_fresh", "quote_input_new");
            append_quote_tag_new_input(before);
        }
    });
    return quote_tag_edit_input_new;
}

function render_quote_edit_pane_submit_button(quote, form) {
    let quote_tag_submit_button = document.createElement("button");
    quote_tag_submit_button.textContent = "Submit";
    quote_tag_submit_button.className = "btn btn-warning";
    quote_tag_submit_button.addEventListener("click", (event) => {
        event.target.setAttribute("disabled", "");
        let form_children = form.children;
        let tags = []
        for (form_child of form_children) {
            if (form_child.className.includes("quote_input") ) {
                if (form_child.value !== undefined && form_child.value !== "") {
                    tags.push(form_child.value);
                }
            }
        }
        form.replaceChildren(make_spinner());
        call_tehbot_api("PATCH", `guilds/${fragment_params["guild_id"]}/quotes/${quote["name"]}`, {"tags": tags}).then((r) => {
            if (!r.success) {
                form.replaceChildren(render_api_error("API Error", `${r["error"]["code"]}: ${r["error"]["msg"]}`));
                console.error(r.error.code + ": " + r.error.msg);
            }
            else {
                let card_wrap = form.parentElement.parentElement.parentElement;
                card_wrap.parentElement.replaceChild(render_quote(r.response.body["quote"]), card_wrap);
            }
        });
    });
    return quote_tag_submit_button;
}

function render_quote_edit_pane(quote) {
    let quote_tag_edit_div = document.createElement("div");
    quote_tag_edit_div.className = "collapse";
    quote_tag_edit_div.id = `quote_${quote["name"]}_tag_edit`;

    let quote_tag_edit_form = document.createElement("form");
    quote_tag_edit_div.append(quote_tag_edit_form);

    for (tag of quote["tags"]) {
        let quote_tag_edit_input = render_quote_tag_edit_input(tag);
        quote_tag_edit_form.append(quote_tag_edit_input);
        // last_input = quote_tag_edit_input;
    }

    let submit_button = render_quote_edit_pane_submit_button(quote, quote_tag_edit_form);
    quote_tag_edit_form.append(submit_button);

    append_quote_tag_new_input(submit_button);

    return quote_tag_edit_div;
}

function render_quote_edit_button(edit_div) {
    let quote_tag_edit_button = document.createElement("button");
    quote_tag_edit_button.textContent = "Edit Tags";
    quote_tag_edit_button.className = "btn btn-primary";
    quote_tag_edit_button.setAttribute("data-bs-toggle", "collapse");
    quote_tag_edit_button.setAttribute("data-bs-target", "#"+edit_div.id);
    quote_tag_edit_button.setAttribute("aria-expanded", "false");
    quote_tag_edit_button.setAttribute("aria-controls", edit_div.id);

    return quote_tag_edit_button;
}

function render_quote_delete_div(quote) {
    let quote_tag_delete_div = document.createElement("div");
    quote_tag_delete_div.className = "collapse";
    quote_tag_delete_div.id = `quote_${quote["name"]}_tag_delete`;

    let quote_tag_delete_confirm_button = document.createElement("button");
    quote_tag_delete_confirm_button.textContent = "Confirm Deletion";
    quote_tag_delete_confirm_button.className = "btn btn-danger";
    quote_tag_delete_confirm_button.addEventListener("click", (event) => {
        quote_tag_delete_div.replaceChildren(make_spinner());
        call_tehbot_api("DELETE", `guilds/${fragment_params["guild_id"]}/quotes/${quote["name"]}`).then((r) => {
            if (!r.success) {
                quote_tag_delete_div.replaceChildren(render_api_error("API Error", `${r["error"]["code"]}: ${r["error"]["msg"]}`));
                console.error(r.error.code + ": " + r.error.msg);
            }
            else {
                quote_tag_delete_div.parentElement.parentElement.remove();
                // let card_wrap = form.parentElement.parentElement.parentElement;
                // card_wrap.parentElement.replaceChild(render_quote(r.response.body["quote"]), card_wrap);
                // card_wrap.parentElement.append(render_add_quote());
            }
        });
    });
    quote_tag_delete_div.append(quote_tag_delete_confirm_button);
    return quote_tag_delete_div;
}

function render_quote_delete_button(delete_div) {
    let quote_tag_delete_button = document.createElement("button");
    quote_tag_delete_button.textContent = "Delete Quote";
    quote_tag_delete_button.className = "btn btn-danger";
    quote_tag_delete_button.setAttribute("data-bs-toggle", "collapse");
    quote_tag_delete_button.setAttribute("data-bs-target", "#"+delete_div.id);
    quote_tag_delete_button.setAttribute("aria-expanded", "false");
    quote_tag_delete_button.setAttribute("aria-controls", delete_div.id);
    return quote_tag_delete_button;
}

//<input class="form-control form-control-lg" type="text" placeholder=".form-control-lg" aria-label=".form-control-lg example">
function render_quote_add_form() {
    let form = document.createElement("form");
    
    let name_input = document.createElement("input");
    name_input.className = "form-control form-control-lg";
    name_input.setAttribute("type", "text");
    name_input.setAttribute("placeholder", "Name");
    form.append(name_input);

    let url_input = document.createElement("input");
    url_input.className = "form-control";
    url_input.setAttribute("type", "url");
    url_input.setAttribute("placeholder", "URL");
    form.append(url_input);
    

    let submit_button = document.createElement("button");
    submit_button.className = "btn btn-success";
    submit_button.textContent = "New Quote";
    submit_button.addEventListener("click", (event) => {
        let quote = {}
        quote["name"] = name_input.value;
        quote["url"] = url_input.value;
        let form_children = form.children;
        let tags = []
        for (form_child of form_children) {
            if (form_child.className.includes("quote_input") ) {
                if (form_child.value !== undefined && form_child.value !== "") {
                    tags.push(form_child.value);
                }
            }
        }
        quote["tags"] = tags;
        form.replaceChildren(make_spinner());
        call_tehbot_api("POST", `guilds/${fragment_params["guild_id"]}/quotes`, quote).then((r) => {
            if (!r.success) {
                form.replaceChildren(render_api_error("API Error", `${r["error"]["code"]}: ${r["error"]["msg"]}`));
                console.error(r.error.code + ": " + r.error.msg);
            }
            else {
                let card_wrap = form.parentElement.parentElement.parentElement;
                card_wrap.parentElement.replaceChild(render_quote(r.response.body["quote"]), card_wrap);
                card_wrap.parentElement.append(render_add_quote());
            }
        });
    });
    form.append(submit_button);
    append_quote_tag_new_input(submit_button);

    return form;
}

function render_add_quote() {
    let quote_wrap_div = document.createElement("div");
    quote_wrap_div.className = "col-xl-2 col-md-3 col-sm-4";
    let quote_card_div = document.createElement("div");
    quote_card_div.className = "card";
    let quote_card_body_div = document.createElement("div");
    quote_card_body_div.className = "card-body";
    quote_card_div.append(quote_card_body_div);

    let quote_tag_add_form = render_quote_add_form();
    quote_card_body_div.append(quote_tag_add_form);

    quote_wrap_div.append(quote_card_div);
    return quote_wrap_div;
}

function render_quote(quote) {
    let quote_wrap_div = document.createElement("div");
    quote_wrap_div.className = "col-xl-2 col-md-3 col-sm-4";
    let quote_card_div = document.createElement("div");
    quote_card_div.className = "card";
    let quote_card_body_div = document.createElement("div");
    quote_card_body_div.className = "card-body";
    quote_card_div.append(quote_card_body_div);

    let quote_img = document.createElement("img");
    quote_img.className = "card-img-top quote_img";
    quote_img.src = quote["url"];
    quote_card_div.append(quote_img);

    let quote_h = document.createElement("h5");
    quote_h.className = "card-title";
    quote_h.textContent = quote["name"];
    quote_card_body_div.append(quote_h);

    let quote_tags_div = document.createElement("div");
    quote_tags_div.className = "flex-wrap quote_tags";

    for (tag of quote["tags"]) {
        let quote_tag_button = render_quote_tag_button(tag);
        quote_tags_div.append(quote_tag_button);
    }

    let quote_tag_edit_div = render_quote_edit_pane(quote);

    quote_card_body_div.append(quote_tags_div);

    let quote_tag_edit_button = render_quote_edit_button(quote_tag_edit_div);


    let quote_tag_delete_div = render_quote_delete_div(quote);
    let quote_tag_delete_button = render_quote_delete_button(quote_tag_delete_div);

    quote_card_div.append(quote_tag_edit_button);
    quote_card_div.append(quote_tag_edit_div);
    quote_card_div.append(quote_tag_delete_button);
    quote_card_div.append(quote_tag_delete_div);

    // quote_li.append(quote_card_div);
    // quote_list_ul.append(quote_li);
    
    quote_wrap_div.append(quote_card_div);
    return quote_wrap_div;
}

function build_controls(pagenum, pagecount, row) {
    let ul = document.createElement("ul");
    ul.className = "nav nav-tabs";

    for (let i = 0 ; i < pagecount ; i++) {
        let li = document.createElement("li");
        li.className = "nav-item";
        let a = document.createElement("a");
        a.className = "nav-link";
        a.textContent = "Page " + (i+1);
        a.setAttribute("aria-current", "page");
        if ( i == pagenum ) {
            a.className = a.className + " active";
        }
        a.addEventListener("click", (event) => {
            event.preventDefault();
            let new_params = fragment_params;
            new_params["pagenum"] = i;
            location.hash = print_fragment_params(new_params);
            do_page_nav();
        });
        li.append(a);
        ul.append(li);
    }
    row.append(ul);
}

function render_guild_quotes_gallery(guild_id, controls_div) {
    let pagenum = 0;
    if ("pagenum" in fragment_params) {
        pagenum = parseInt(fragment_params["pagenum"]);
    }

    let quote_row_div = document.createElement("div");
    quote_row_div.className = "row mt-4";
    quote_row_div.replaceChildren(make_spinner());

    let request_body = {};
    request_body["offset"] = pagenum*QUOTES_PER_PAGE;
    request_body["count"] = QUOTES_PER_PAGE;
    if (fragment_params["search"] !== undefined) {
        request_body["terms"] = fragment_params["search"].split(",");
    }
    call_tehbot_api("POST", `guilds/${guild_id}/quotes/search`, request_body).then((r) => {
        quote_row_div.textContent = "";
        if (!r.success) {
            quote_row_div.replaceChildren(render_api_error("API Error", `${r["error"]["code"]}: ${r["error"]["msg"]}`));
            // quote_row_div.textContent = "Error: " + r.error.msg;
            console.error(r.error.code + ": " + r.error.msg);
        }
        else {
            let data = r["response"]["body"];
            //let quote_list_ul = document.createElement("ul");
            for (quote of data["quotes"]) {
                quote_row_div.append(render_quote(quote));
            }
            quote_row_div.append(render_add_quote());
            let pagecount = Math.ceil(data["total_hits"]/QUOTES_PER_PAGE);
            build_controls(pagenum, pagecount, controls_div);
        }
    });
    return quote_row_div;
}

function render_guild_quotes_search() {
    let form = document.createElement("form");
    form.className = "d-flex";
    form.setAttribute("role", "search");

    //<input class="form-control me-2" type="search" placeholder="Search" aria-label="Search">
    let search_input = document.createElement("input");
    search_input.className = "form-control me-2";
    search_input.setAttribute("type", "search");
    search_input.setAttribute("placeholder", "Search Quotes");
    search_input.setAttribute("aria-label", "Search Quotes");
    form.append(search_input);

    //<button class="btn btn-outline-success" type="submit">Search</button>
    let search_button = document.createElement("button");
    search_button.className = "btn btn-outline-success";
    search_button.setAttribute("type", "submit");
    search_button.textContent = "Search";
    search_button.addEventListener("click", (event) => {
        event.preventDefault();
        let params = {};
        params["nav"] = "quotes";
        params["guild_id"] = fragment_params["guild_id"];
        params["search"] = search_input.value;
        location.hash = print_fragment_params(params);
        do_page_nav();
    });
    form.append(search_button);

    return form;
}


function render_guild_quotes_navbar() {
    //<nav class="navbar navbar-expand-lg bg-light" id="navbar">
    let navbar = document.createElement("nav");
    navbar.className = "navbar navbar-expand-lg bg-light";
    navbar.setAttribute("id", "navbar");

    //<div class="container-fluid">
    let navbar_container_div = document.createElement("div");
    navbar_container_div.className = "container-fluid";
    navbar.append(navbar_container_div);

    //<span class="navbar-brand">Quote Management
    let navbar_titlespan = document.createElement("span");
    navbar_titlespan.className = "navbar-brand";
    navbar_titlespan.textContent = "Quote Management";
    navbar_container_div.append(navbar_titlespan);

    //<button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
    let navbar_toggle_button = document.createElement("button");
    navbar_toggle_button.className = "navbar-toggler";
    navbar_toggle_button.setAttribute("type", "button");
    navbar_toggle_button.setAttribute("data-bs-toggle", "collapse");
    navbar_toggle_button.setAttribute("data-bs-target", "#navbarSupportedContent");
    navbar_toggle_button.setAttribute("aria-controls", "navbarSupportedContent");
    navbar_toggle_button.setAttribute("aria-expanded", "false");
    navbar_toggle_button.setAttribute("aria-label", "Toggle navigation");
    navbar_container_div.append(navbar_toggle_button);

    //<span class="navbar-toggler-icon">
    let navbar_toggle_button_icon = document.createElement("span");
    navbar_toggle_button_icon.className = "navbar-toggler-icon";
    navbar_toggle_button.append(navbar_toggle_button_icon);

    //<div class="collapse navbar-collapse" id="navbarSupportedContent">
    let navbar_collapsed_div = document.createElement("div");
    navbar_collapsed_div.className = "collapse navbar-collapse";
    navbar_collapsed_div.setAttribute("id", "navbarSupportedContent");
    navbar_container_div.append(navbar_collapsed_div);

    //<ul class="navbar-nav me-auto mb-2 mb-lg-0"></ul>
    let navbar_links_ul = document.createElement("ul");
    navbar_links_ul.className = "navbar-nav me-auto mb-2 mb-lg-0";
    navbar_collapsed_div.append(navbar_links_ul);

    navbar_collapsed_div.append(render_guild_quotes_search());

    return navbar;
}

QUOTES_PER_PAGE = 11;

function render_guild_quotes_nav_breadcrumbs() {
    let last = render_guild_nav_breadcrumbs();
    let params = {};
    params["nav"] = "quotes";
    params["guild_id"] = fragment_params["guild_id"];
    last.push(["Quotes", print_fragment_params(params)]);
    return last;
}


function render_guild_quotes_nav() {
    // sessionStorage.setItem("current_quotes_guild_id", guild_id);
    // sessionStorage.setItem("current_quotes_page", pagenum);

    // let content_div = document.getElementById("content");

    let quote_navbar = render_guild_quotes_navbar();

    let quote_controls_row_div = document.createElement("div");
    quote_controls_row_div.className = "row mt-2";

    let quote_row_div = render_guild_quotes_gallery(fragment_params["guild_id"], quote_controls_row_div);

    return {"content": [quote_navbar, quote_controls_row_div, quote_row_div], "breadcrumbs": render_guild_quotes_nav_breadcrumbs()};
}