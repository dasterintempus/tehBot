// function render_breadcrumb(name, anchor) {
//     let breadcrumb_li = document.createElement("li");
//     breadcrumb_li.className = "breadcrumb-item";
//     let breadcrumb_a = document.createElement("a");
//     breadcrumb_a.setAttribute("href", "#");
//     breadcrumb_a.addEventListener("click", (event) => {
//         event.preventDefault();
//         location.hash = anchor;
//         do_page_nav();
//     });
//     breadcrumb_a.textContent = name;
//     breadcrumb_li.append(breadcrumb_a);
//     return breadcrumb_li;
// }

function _apply_page_nav(f) {
    let results = f();
    // page_breadcrumb_container.replaceChildren();
    // let page_breadcrumb_ol = document.createElement("ol");
    // page_breadcrumb_ol.className = "breadcrumb";
    // for (breadcrumb of results["breadcrumbs"]) {
    //     page_breadcrumb_ol.append(render_breadcrumb(breadcrumb[0], breadcrumb[1]));
    // }
    // let cur_breadcrumb = page_breadcrumb_ol.lastChild;
    // cur_breadcrumb.classList.add("active");
    // cur_breadcrumb.setAttribute("aria-current", "page");
    // page_breadcrumb_container.append(page_breadcrumb_ol);
    // page_breadcrumb_container.append(document.createElement("hr"));
    content_div.replaceChildren(...results["content"]);
}

function do_page_nav() {
    let fragment = location.hash;
    fragment_params = parse_fragment_params(fragment);
    if ( ! ("nav" in fragment_params) ) {
        _apply_page_nav(render_guilds_list_nav);
    }
    else {
        let nav = fragment_params["nav"];
        if (nav == "guild") {
            _apply_page_nav(render_guild_nav);
        }
        else if (nav == "quotes") {
            _apply_page_nav(render_guild_quotes_nav);
        }
        else if (nav == "reinvite") {
            _apply_page_nav(render_guild_reinvite_nav);
        }
    }
}

function render_guilds_list_nav_breadcrumbs() {
    let params = {};
    return [["Home", print_fragment_params(params)]];
}



function render_guilds_list_nav() {
    let button_row_div = document.createElement("div");
    let guilds = creds["guilds"];
    for (guild_id in guilds) {
        let guild_button = document.createElement("button");
        guild_button.className = "btn btn-primary";
        guild_button.textContent = guilds[guild_id]["name"];
        button_row_div.append(guild_button);
        guild_button.addEventListener("click", () => {
            for (child of button_row_div.children) {
                child.setAttribute("disabled", "");
            }
            location.hash = encodeURIComponent(`guild_id=${guild_id}&nav=guild`);
            do_page_nav();
            // let quote_row_div = render_guild_quotes(guild_id);
            // content_div.append(quote_row_div);
        });
    }
    return {"content": [button_row_div], "breadcrumbs": render_guilds_list_nav_breadcrumbs()};
}


function render_guild_nav_breadcrumbs() {
    let last = render_guilds_list_nav_breadcrumbs();
    let params = {};
    params["nav"] = "guild";
    params["guild_id"] = fragment_params["guild_id"];
    let guild_name = creds["guilds"][params["guild_id"]]["name"];
    last.push([`Guild: ${guild_name}`, print_fragment_params(params)]);
    return last;
}

function render_guild_nav() {
    let guild_id = fragment_params["guild_id"];
    let button_row_div = document.createElement("div");
    let creds = JSON.parse(sessionStorage.getItem("tehbot_creds"));
    if (creds["guild_perms"][guild_id].includes("admin") || creds["guild_perms"][guild_id].includes("quotemod")) {
        let button = document.createElement("button");
        button.className = "btn btn-primary";
        button.textContent = "Manage Quotes";
        button_row_div.append(button);
        button.addEventListener("click", () => {
            for (child of button_row_div.children) {
                child.setAttribute("disabled", "");
            }
            location.hash = encodeURIComponent(`guild_id=${guild_id}&nav=quotes`);
            do_page_nav();
            // let quote_row_div = render_guild_quotes(guild_id);
            // content_div.append(quote_row_div);
        });
    }
    if (creds["guild_perms"][guild_id].includes("admin") || creds["guild_perms"][guild_id].includes("reinvite")) {
        let button = document.createElement("button");
        button.className = "btn btn-primary";
        button.textContent = "Generate Invite Link";
        button_row_div.append(button);
        button.addEventListener("click", () => {
            for (child of button_row_div.children) {
                child.setAttribute("disabled", "");
            }
            location.hash = encodeURIComponent(`guild_id=${guild_id}&nav=reinvite`);
            do_page_nav();
            // let quote_row_div = render_guild_quotes(guild_id);
            // content_div.append(quote_row_div);
        });
    }
    return {"content": [button_row_div], "breadcrumbs": render_guild_nav_breadcrumbs()};
}
