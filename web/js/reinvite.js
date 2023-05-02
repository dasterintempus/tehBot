function render_guild_reinvite_nav() {

    let reinvite_div = document.createElement("div");
    call_tehbot_api("POST", `guilds/${guild_id}/reinvite`).then((r) => {
        reinvite_div.textContent = "";
        if (!r.success) {
            reinvite_div.replaceChildren(render_api_error("API Error", `${r["error"]["code"]}: ${r["error"]["msg"]}`));
            // quote_row_div.textContent = "Error: " + r.error.msg;
            console.error(r.error.code + ": " + r.error.msg);
        }
        else {
            let data = r["response"]["body"];
            let reinvite_link_a = document.createElement("a");
            reinvite_link_a.href = data["link"];
            reinvite_link_a.textContent = data["link"];
        }
    });


    return {"content": [reinvite_div], "breadcrumbs": null};
}