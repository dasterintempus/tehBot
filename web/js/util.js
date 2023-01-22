//https://attacomsian.com/blog/javascript-generate-random-string
function random_string(length = 8) {
    // Declare all characters
    let chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';

    // Pick characers randomly
    let str = '';
    for (let i = 0; i < length; i++) {
        str += chars.charAt(Math.floor(Math.random() * chars.length));
    }

    return str;

};

function make_spinner() {
    let spinner = document.createElement("div");
    spinner.className = "spinner-border";
    spinner.setAttribute("role", "status");
    let status = document.createElement("span");
    status.className = "visually-hidden";
    status.textContent = "Loading...";
    spinner.append(status);
    return spinner
}

function parse_fragment_params(fragment) {
    let out = {};
    for (paramstr of fragment.replace("#", "").split("%26")) {
        if (paramstr !== "") {
            let kv = paramstr.split("%3D");
            let k = kv[0];
            let v = kv[1];
            out[k] = v;
        }
    }
    return out;
}

// function render_breadcrumb_anchor(obj) {
//     return print_fragment_params(obj);
// }

function print_fragment_params(params) {
    let out = []
    for (key in params) {
        out.push(`${key}%3D${params[key]}`);
    }
    return "#" + out.join("%26");
}

function render_api_error(title, body, details=null) {
    let error_div = document.createElement("div");
    error_div.className = "alert alert-danger";
    error_div.setAttribute("role", "alert");
    let error_heading = document.createElement("h4");
    error_heading.className = "alert-heading";
    error_heading.textContent = title;
    error_div.append(error_heading);
    let error_p = document.createElement("p");
    error_p.textContent = body;
    // if (r["error"]["code"] == "DiscordGetTokenFail") {
    //     error_p.textContent = "tehBot was unable to authenticate you to Discord."
    // }
    // else if (r["error"]["code"] == "NoGuilds") {
    //     error_p.textContent = "tehBot did not find any known Discord Servers (aka Guilds) that you are a part of."
    // }
    // else if (r["error"]["code"] == "NoRoles") {
    //     error_p.textContent = "tehBot did not find admin roles for you on the known Discord Servers (aka Guilds) that you are a part of."
    // }
    // else {
    //     error_p.textContent = "tehBot experienced an unknown error while trying to authenticate you."
    // }
    error_div.append(error_p);
    if (details !== null) {
        error_div.append(document.createElement("hr"));
        let error_details_p = document.createElement("p");
        error_details_p.claassName = "mb-0";
        error_details_p.textContent = details;
        // error_details_p.textContent = `API Error ${r["error"]["code"]}: ${r["error"]["msg"]}`;
        error_div.append(error_details_p);
    }

    return error_div;
}