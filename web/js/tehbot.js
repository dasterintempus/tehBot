TEHBOT_API_URL="{{ tehbot_api_url }}"
DISCORD_OAUTH_URL="{{ discord_oauth_url }}"

function do_discord_oauth() {
    sessionStorage.setItem("saved_fragment", location.hash);
    let state_param = random_string();
    sessionStorage.setItem("discord_oauth_state", state_param);
    location.href = DISCORD_OAUTH_URL+`&state=${state_param}`;
}

async function call_tehbot_api(method, url, body) {
    let headers = {
        "Content-Type": "application/json"
    }
    let creds = sessionStorage.getItem("tehbot_creds");
    if (creds !== null) {
        headers["X-teh-Auth"] = JSON.parse(creds)["token"];
    }
    const response = fetch(TEHBOT_API_URL+url, {
        method: method,
        cache: "no-cache",
        headers: headers,
        body: JSON.stringify(body)
    });
    return response.then((r) => {
        if (r.ok) {
            return r.json().then((data) => {
                return {"success": true, "response": {"code": r.status, "body": data}};
            })
            .catch((error) => {
                console.error(error);
                return {"success": false, "error": {"code": "NotJson", "message": "API did not return valid JSON..."}};
            });
        }
        else {
            return r.json().then((data) => {
                if (data["error"]["code"] == "InvalidToken" || data["error"]["code"] == "ExpiredToken") {
                    sessionStorage.removeItem("tehbot_creds");
                    do_discord_oauth();
                }
                return {"success": false, "error": data["error"]};
            })
            .catch((error) => {
                console.error(error);
                return {"success": false, "error": {"code": "NotJson", "message": "API did not return valid JSON..."}};
            });
        }
    })
    .catch((error) => {
        console.error(error);
        return {"success": false, "error": {"code": "NetworkFailure", "message": "API call did not complete."}};
    });
}

// async function show_quotes_page(credstr) {
//     let creds = JSON.parse(credstr);
//     let button_row_div = document.createElement("div");
//     let guilds = creds["guilds"];
//     for (guild_id in guilds) {
//         let guild_button = document.createElement("button");
//         guild_button.className = "btn btn-primary";
//         guild_button.textContent = guilds[guild_id]["name"];
//         button_row_div.append(guild_button);
//         guild_button.addEventListener("click", () => {
//             let quote_row_div = render_guild_quotes(guild_id);
//             content_div.append(quote_row_div);
//         });
//     }
//     content_div.replaceChildren(button_row_div);
// }

async function do_tehbot_setup() {
    discord_code = query_vals.get("code");
    call_tehbot_api("POST", "auth/token", {"code": discord_code}).then((r) => {
        if (r.success) {
            sessionStorage.setItem("tehbot_creds", JSON.stringify(r.response.body));
            let user_display_name = JSON.parse(sessionStorage.getItem("tehbot_creds"))["user_display_name"];
            content_div.textContent = `Authenticated to tehBot API as ${user_display_name}! Reloading page shortly...`;

            setTimeout(() => {location.search = "";}, 2500);
            
            // let credstr = sessionStorage.getItem("tehbot_creds");
            // get_quotes(credstr);
        }
        else {
            // let error_div = document.createElement("div");
            // error_div.className = "alert alert-danger";
            // error_div.setAttribute("role", "alert");
            // let error_heading = document.createElement("h4");
            // error_heading.className = "alert-heading";
            // error_heading.textContent = "OAuth Failure";
            // error_div.append(error_heading);
            // let error_p = document.createElement("p");
            let error_msg = "";
            if (r["error"]["code"] == "DiscordGetTokenFail") {
                error_msg = "tehBot was unable to authenticate you to Discord."
            }
            else if (r["error"]["code"] == "NoGuilds") {
                error_msg = "tehBot did not find any known Discord Servers (aka Guilds) that you are a part of."
            }
            else if (r["error"]["code"] == "NoRoles") {
                error_msg = "tehBot did not find admin roles for you on the known Discord Servers (aka Guilds) that you are a part of."
            }
            else {
                error_msg = "tehBot experienced an unknown error while trying to authenticate you."
            }
            let error_div = render_api_error("OAuth Failure", error_msg, `API Error ${r["error"]["code"]}: ${r["error"]["msg"]}`)
            // error_div.append(error_p);
            // error_div.append(document.createElement("hr"));
            // let error_details_p = document.createElement("p");
            // error_details_p.claassName = "mb-0";
            // error_details_p.textContent = `API Error ${r["error"]["code"]}: ${r["error"]["msg"]}`;
            // error_div.append(error_details_p);
            content_div.replaceChildren(error_div);
        }
    });
}


addEventListener("DOMContentLoaded", (event) => {
    content_div = document.getElementById("content");
    // page_breadcrumb_container = document.getElementById("page_breadcrumb");

    let saved_fragment = sessionStorage.getItem("saved_fragment");
    if (saved_fragment !== null) {
        location.hash = saved_fragment;
        sessionStorage.removeItem("saved_fragment");
    }

    query_vals = new URLSearchParams(location.search);
    let credstr = sessionStorage.getItem("tehbot_creds");
    if ( credstr !== null ) {
        creds = JSON.parse(credstr);
        do_page_nav();
        // if ( !query_vals.has("nav") ) {
        //     content_div.replaceChildren(render_guilds_list_nav(creds));
        // }
        // else {
        //     let nav = query_vals.get("nav");
        //     if (nav == "guild") {
        //         guild_id = query_vals.get("guild_id");
        //         content_div.replaceChildren(render_guild_nav(creds, guild_id));
        //     }
        //     else if (nav == "quotes") {
        //         guild_id = query_vals.get("guild_id");
        //         content_div.replaceChildren(render_guild_quotes_nav(creds, guild_id));
        //     }
        // }
    }
    else {
        if ( query_vals.has("code") ) {
            if ( query_vals.has("state") && query_vals.get("state") == sessionStorage.getItem("discord_oauth_state")) {
                sessionStorage.removeItem("discord_oauth_state");
                content_div.replaceChildren(make_spinner());
                do_tehbot_setup();
            }
            else {
                content_div.textContent = "Unable to validate Discord OAuth state. Not proceeding.";
            }
        }
        else {
            let auth_button = document.createElement("button");
            auth_button.textContent = "Authenticate with Discord OAuth";
            auth_button.className = "btn btn-dark btn-lg";
            auth_button.addEventListener("click", () => {
                content_div.replaceChildren(make_spinner());
                do_discord_oauth();
            });
            content_div.append(auth_button);
        }
    }
})