import io
import json
from tehbot.chart.render import render_chart

def chart_show():
    filebody = io.BytesIO()
    print("Rendering Chart")
    chart_image, chart_errors = render_chart()
    print("Saving Chart")
    chart_image.save(filebody, "PNG")
    print("Done Saving Chart")
    filebody.seek(0)
    print("Done seek(0)ing Chart filebody")
    files = {}
    files["file[0]"] = ("chart.png", filebody)
    outbody = {
        "content": "\n".join(chart_errors),
        "embeds": [{
            "image": {
                "url": "attachment://chart.png"
            }
        }]
    }
    files["payload_json"] = ("", json.dumps(outbody), "application/json")
    return True, {"files": files}