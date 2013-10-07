import numpy

from gui.vector import V

def calibration_transformation_matrix(width, height, gui_width, gui_height, corners):
    transformation_matrix = numpy.zeros((height, width), dtype=V)
    for y in range(0, height):
        for x in range(0, width):
            ap = V.point_line_projection(corners['top_left'], corners['top_right'], V(x, y))
            bp = V.point_line_projection(corners['top_right'], corners['bottom_right'], V(x, y))
            cp = V.point_line_projection(corners['bottom_left'], corners['bottom_right'], V(x, y))
            dp = V.point_line_projection(corners['top_left'], corners['bottom_left'], V(x, y))
            ap_abs = ap.abs()
            bp_abs = bp.abs()
            cp_abs = cp.abs()
            dp_abs = dp.abs()

            t = cp - corners['bottom_left']
            l = t.abs() / (corners['bottom_right']-corners['bottom_left']).abs()
            if t*V(1,0) < 0: l = -l

            t = ap-corners['top_left']
            m = t.abs() / (corners['top_right']-corners['top_left']).abs()
            if t*V(1,0) < 0: m = -m
                
            p_tx = l * (gui_width-1) * ap_abs/(ap_abs + cp_abs) + m * (gui_width-1) * cp_abs/(ap_abs + cp_abs)

            t = dp-corners['top_left']
            n = t.abs() / (corners['bottom_left']-corners['top_left']).abs()
            if t*V(0,1) < 0: n = -n

            t = bp-corners['top_right']
            o = t.abs() / (corners['top_right']-corners['bottom_right']).abs()
            if t*V(0,1) < 0: o = -o

            p_ty = n * (gui_height-1) * dp_abs/(dp_abs + bp_abs) + o * (gui_height-1) * bp_abs/(dp_abs + bp_abs)
            transformation_matrix[y][x] = V(p_tx, p_ty)
    return transformation_matrix
