import numpy as np
from scipy.optimize import minimize


def assign_force_vector(f_in, F_in, J_in, Seg_in, Ret_in, lb_in, ub_in):
    """
    Assign forces to cylinders given target forces/moments.
    F_in must be shape (6,) in format [0, 0, axial_force, moment_x, moment_y, 0].

    Args:
        f_in (ndarray): previous force vector, shape (n,)
        F_in (ndarray): target [0,0,Fz,Mx,My,0]
        J_in (ndarray): Jacobian matrix, shape (6, n)
        Seg_in (ndarray): segmentation labels, shape (n,)
        Ret_in (ndarray): boolean array, True means retracted (inactive)
        lb_in, ub_in (float or array): lower/upper bounds for pressures

    Returns:
        f_out (ndarray): updated force vector, shape (n,)
        success (bool): whether optimization succeeded
        message (str): diagnostic message from optimizer (optional)
    """
    n = len(f_in)
    active = ~Ret_in
    m = active.sum()

    # build equal-segment constraints (J2 x = 0)
    k = int(np.max(Seg_in))
    J2_rows = []
    for seg in range(1, k + 1):
        idx = np.where(Seg_in == seg)[0]
        if len(idx) > 1 and np.all(np.logical_not(Ret_in[idx])):
            ref = idx[0]
            for j in idx[1:]:
                row = np.zeros(n)
                row[ref] = 1
                row[j] = -1
                J2_rows.append(row)
    J2 = np.vstack(J2_rows) if J2_rows else np.zeros((0, n))
    F2 = np.zeros(J2.shape[0])

    # bounds for active cylinders
    lb = np.full(m, lb_in) if np.isscalar(lb_in) else np.array(lb_in)
    ub = np.full(m, ub_in) if np.isscalar(ub_in) else np.array(ub_in)
    bounds = list(zip(lb, ub))

    # select relevant Jacobian rows (z-force, Mx, My)
    rows = [2, 3, 4]
    J_sel = J_in[rows, :]
    F_sel = F_in[rows]

    # build equality constraints Aeq x = beq
    Aeq = np.vstack((J_sel, J2))[:, active]
    beq = np.concatenate((F_sel, F2))

    # initial guess: distribute axial force equally
    f0 = np.full(m, F_in[2] / m)

    # objective: minimal change from f0
    def objective(x):
        return np.sum((x - f0) ** 2)

    cons = {"type": "eq", "fun": lambda x: Aeq.dot(x) - beq}
    res = minimize(
        objective,
        f0,
        method="SLSQP",
        bounds=bounds,
        constraints=cons,
        options={"maxiter": 500, "ftol": 1e-9},
    )

    if not res.success:
        return f_in.copy(), False, res.message

    f_out = f_in.copy()
    f_out[active] = res.x
    return f_out, True, res.message
