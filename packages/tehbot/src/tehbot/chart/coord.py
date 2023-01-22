def compute_pos(coords):
    from .render import TOP_POINT, RIGHT_POINT, LEFT_POINT
    x = (coords[0]*TOP_POINT[0]) + (coords[1]*RIGHT_POINT[0]) + (coords[2]*LEFT_POINT[0])
    y = (coords[0]*TOP_POINT[1]) + (coords[1]*RIGHT_POINT[1]) + (coords[2]*LEFT_POINT[1])
    return x, y

def cart_to_bary(cart_p, bary_refs):
    b1 = (
        (
            (bary_refs[1][1] - bary_refs[2][1]) *
            (cart_p[0] - bary_refs[2][0])
        ) + (
            (bary_refs[2][0] - bary_refs[1][0]) *
            (cart_p[1] - bary_refs[2][1])
        )
    ) / (
        (
            (bary_refs[1][1] - bary_refs[2][1]) *
            (bary_refs[0][0] - bary_refs[2][0])
        ) + (
            (bary_refs[2][0] - bary_refs[1][0]) *
            (bary_refs[0][1] - bary_refs[2][1])
        )
    )
    b2 = (
        (
            (bary_refs[2][1] - bary_refs[0][1]) *
            (cart_p[0] - bary_refs[2][0])
        ) + (
            (bary_refs[0][0] - bary_refs[2][0]) *
            (cart_p[1] - bary_refs[2][1])
        )
    ) / (
        (
            (bary_refs[1][1] - bary_refs[2][1]) *
            (bary_refs[0][0] - bary_refs[2][0])
        ) + (
            (bary_refs[2][0] - bary_refs[1][0]) *
            (bary_refs[0][1] - bary_refs[2][1])
        )
    )
    b3 = 1 - b1 - b2
    return b1, b2, b3

def bary_to_color(bary_p, colors):
    r = int(colors[0][0] * bary_p[0] + colors[1][0] * bary_p[1] + colors[2][0] * bary_p[2])
    g = int(colors[0][1] * bary_p[0] + colors[1][1] * bary_p[1] + colors[2][1] * bary_p[2])
    b = int(colors[0][2] * bary_p[0] + colors[1][2] * bary_p[1] + colors[2][2] * bary_p[2])
    a = int(colors[0][3] * bary_p[0] + colors[1][3] * bary_p[1] + colors[2][3] * bary_p[2])
    return (r,g,b,a)