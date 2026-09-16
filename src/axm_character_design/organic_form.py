from __future__ import annotations
import hashlib, json, math
from pathlib import Path

SCHEMA = "axm.character-organic-form-study/v0.1"
STUDY_ID = "character-neutral-a-001"
TRUTH_STATE = "FORM_STUDY_NOT_RIGGED_NOT_ANIMATED"

def _v(x,y,z): return [float(x), float(y), float(z)]

def neutral_character_study():
    landmarks = {
        "neck_base": _v(0,0,1.52), "neck_top": _v(0,0,1.59),
        "shoulder_L": _v(-0.22,0,1.48), "elbow_L": _v(-0.48,0,1.32), "wrist_L": _v(-0.69,0,1.18), "hand_tip_L": _v(-0.76,0,1.13),
        "shoulder_R": _v(0.22,0,1.48), "elbow_R": _v(0.48,0,1.32), "wrist_R": _v(0.69,0,1.18), "hand_tip_R": _v(0.76,0,1.13),
        "hip_L": _v(-0.11,0,0.92), "knee_L": _v(-0.10,0,0.52), "ankle_L": _v(-0.09,0,0.12), "toe_L": _v(-0.09,0.18,0.08),
        "hip_R": _v(0.11,0,0.92), "knee_R": _v(0.10,0,0.52), "ankle_R": _v(0.09,0,0.12), "toe_R": _v(0.09,0.18,0.08),
    }
    segments = [
        {"id":"neck","a":"neck_base","b":"neck_top","radius_a":0.085,"radius_b":0.08},
        {"id":"upper_arm_L","a":"shoulder_L","b":"elbow_L","radius_a":0.075,"radius_b":0.065},
        {"id":"lower_arm_L","a":"elbow_L","b":"wrist_L","radius_a":0.065,"radius_b":0.050},
        {"id":"hand_L","a":"wrist_L","b":"hand_tip_L","radius_a":0.055,"radius_b":0.045},
        {"id":"upper_arm_R","a":"shoulder_R","b":"elbow_R","radius_a":0.075,"radius_b":0.065},
        {"id":"lower_arm_R","a":"elbow_R","b":"wrist_R","radius_a":0.065,"radius_b":0.050},
        {"id":"hand_R","a":"wrist_R","b":"hand_tip_R","radius_a":0.055,"radius_b":0.045},
        {"id":"thigh_L","a":"hip_L","b":"knee_L","radius_a":0.105,"radius_b":0.085},
        {"id":"shin_L","a":"knee_L","b":"ankle_L","radius_a":0.082,"radius_b":0.055},
        {"id":"foot_L","a":"ankle_L","b":"toe_L","radius_a":0.065,"radius_b":0.075},
        {"id":"thigh_R","a":"hip_R","b":"knee_R","radius_a":0.105,"radius_b":0.085},
        {"id":"shin_R","a":"knee_R","b":"ankle_R","radius_a":0.082,"radius_b":0.055},
        {"id":"foot_R","a":"ankle_R","b":"toe_R","radius_a":0.065,"radius_b":0.075},
    ]
    masses = [
        {"id":"pelvis","center":_v(0,0,0.98),"radii":_v(0.18,0.12,0.18)},
        {"id":"ribcage","center":_v(0,0,1.30),"radii":_v(0.24,0.14,0.29)},
        {"id":"head","center":_v(0,0,1.70),"radii":_v(0.11,0.10,0.14)},
    ]
    flex = [
        {"id":"neck","landmark":"neck_base"}, {"id":"shoulder_L","landmark":"shoulder_L"}, {"id":"elbow_L","landmark":"elbow_L"},
        {"id":"wrist_L","landmark":"wrist_L"}, {"id":"shoulder_R","landmark":"shoulder_R"}, {"id":"elbow_R","landmark":"elbow_R"},
        {"id":"wrist_R","landmark":"wrist_R"}, {"id":"hip_L","landmark":"hip_L"}, {"id":"knee_L","landmark":"knee_L"},
        {"id":"ankle_L","landmark":"ankle_L"}, {"id":"hip_R","landmark":"hip_R"}, {"id":"knee_R","landmark":"knee_R"},
        {"id":"ankle_R","landmark":"ankle_R"},
    ]
    return {
        "schema": SCHEMA,
        "study_id": STUDY_ID,
        "pose": "NEUTRAL_A_REST",
        "coordinate_system": {"x":"+right","y":"+forward","z":"+up","units":"meter"},
        "intent": "stylized_human_like_biped_form_study",
        "landmarks": landmarks,
        "segments": segments,
        "masses": masses,
        "flex_zones": [{**z, "status":"DECLARED_NOT_DEFORMATION_TESTED"} for z in flex],
        "design_constraints": {
            "authored_head_top_m": 1.84,
            "shoulder_width_m": 0.44,
            "hip_width_m": 0.22,
            "a_pose_down_angle_deg_range": [20.0, 40.0],
            "bilateral_tolerance_m": 1e-9,
        },
        "donor": {
            "repository":"mike-axiom-mir/axm-collaboration-platform",
            "commit":"27757ace6133b243a200b0463e427c8b04d5a8e3",
            "path":"tools/rigging-retargeting-studio/README.md",
            "license":"Apache-2.0",
            "use":"explicit landmark/role discipline only",
            "status":"DONOR_HINT_NOT_INHERITED_PASS",
        },
        "truth_state": TRUTH_STATE,
    }

def canonical_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def _sub(a,b): return [a[i]-b[i] for i in range(3)]
def _add(a,b): return [a[i]+b[i] for i in range(3)]
def _mul(a,s): return [a[i]*s for i in range(3)]
def _dot(a,b): return sum(a[i]*b[i] for i in range(3))
def _cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def _norm(v):
    n=math.sqrt(_dot(v,v))
    if n == 0: raise ValueError("zero-length vector")
    return [x/n for x in v]

def validate_study(study):
    if study.get("schema") != SCHEMA: raise ValueError("wrong schema")
    if study.get("truth_state") != TRUTH_STATE: raise ValueError("truth state drift")
    lm=study["landmarks"]; tol=study["design_constraints"]["bilateral_tolerance_m"]
    for base in ["shoulder","elbow","wrist","hand_tip","hip","knee","ankle","toe"]:
        l,r=lm[f"{base}_L"],lm[f"{base}_R"]
        if abs(l[0]+r[0])>tol or abs(l[1]-r[1])>tol or abs(l[2]-r[2])>tol:
            raise ValueError(f"bilateral symmetry failed: {base}")
    if not study["design_constraints"]["shoulder_width_m"] > study["design_constraints"]["hip_width_m"]:
        raise ValueError("shoulder/hip hierarchy failed")
    top=study["masses"][2]["center"][2]+study["masses"][2]["radii"][2]
    if abs(top-study["design_constraints"]["authored_head_top_m"]) > 1e-9:
        raise ValueError("authored height drift")
    dx=abs(lm["wrist_R"][0]-lm["shoulder_R"][0]); dz=lm["shoulder_R"][2]-lm["wrist_R"][2]
    angle=math.degrees(math.atan2(dz,dx))
    lo,hi=study["design_constraints"]["a_pose_down_angle_deg_range"]
    if not lo <= angle <= hi: raise ValueError("A-pose arm angle outside gate")
    if lm["toe_R"][1] <= lm["ankle_R"][1]: raise ValueError("foot must project forward")
    segids={s["id"] for s in study["segments"]}
    if len(segids)!=len(study["segments"]): raise ValueError("duplicate segment")
    for s in study["segments"]:
        if s["a"] not in lm or s["b"] not in lm: raise ValueError("unknown landmark")
        if s["radius_a"]<=0 or s["radius_b"]<=0: raise ValueError("non-positive radius")
    if any(z["status"]!="DECLARED_NOT_DEFORMATION_TESTED" for z in study["flex_zones"]):
        raise ValueError("flex truth-state drift")
    return {"a_pose_down_angle_deg":angle,"flex_zone_count":len(study["flex_zones"])}

def _segment_mesh(a,b,ra,rb,sides=10):
    w=_norm(_sub(b,a))
    helper=[0.0,0.0,1.0] if abs(w[2])<0.9 else [0.0,1.0,0.0]
    u=_norm(_cross(w,helper)); v=_cross(w,u)
    verts=[]
    for center,r in ((a,ra),(b,rb)):
        for i in range(sides):
            ang=2*math.pi*i/sides
            radial=_add(_mul(u,math.cos(ang)*r),_mul(v,math.sin(ang)*r))
            verts.append(_add(center,radial))
    verts.extend([list(a),list(b)])
    faces=[]
    for i in range(sides):
        j=(i+1)%sides
        faces.append([i,j,sides+j]); faces.append([i,sides+j,sides+i])
        faces.append([2*sides,i,j]); faces.append([2*sides+1,sides+j,sides+i])
    return verts,faces

def _ellipsoid_mesh(center,radii,slices=12,stacks=6):
    verts=[[center[0],center[1],center[2]+radii[2]]]
    for st in range(1,stacks):
        phi=math.pi*st/stacks
        sp,cp=math.sin(phi),math.cos(phi)
        for i in range(slices):
            th=2*math.pi*i/slices
            verts.append([center[0]+radii[0]*sp*math.cos(th),center[1]+radii[1]*sp*math.sin(th),center[2]+radii[2]*cp])
    south=len(verts); verts.append([center[0],center[1],center[2]-radii[2]])
    faces=[]
    for i in range(slices):
        j=(i+1)%slices
        faces.append([0,1+i,1+j])
    for st in range(stacks-2):
        a0=1+st*slices; b0=a0+slices
        for i in range(slices):
            j=(i+1)%slices
            faces.append([a0+i,b0+i,b0+j]); faces.append([a0+i,b0+j,a0+j])
    last=1+(stacks-2)*slices
    for i in range(slices):
        j=(i+1)%slices
        faces.append([south,last+j,last+i])
    return verts,faces

def build_mesh(study=None):
    study=study or neutral_character_study(); validate_study(study)
    verts=[]; faces=[]; regions=[]
    def add_region(rid,vm,fm):
        off=len(verts); start=len(faces)
        verts.extend(vm); faces.extend([[x+off for x in f] for f in fm])
        regions.append({"id":rid,"vertex_start":off,"vertex_count":len(vm),"face_start":start,"face_count":len(fm)})
    lm=study["landmarks"]
    for m in study["masses"]: add_region(m["id"], *_ellipsoid_mesh(m["center"],m["radii"]))
    for s in study["segments"]: add_region(s["id"], *_segment_mesh(lm[s["a"]],lm[s["b"]],s["radius_a"],s["radius_b"]))
    return {"vertices":verts,"faces":faces,"regions":regions}

def mesh_checks(mesh):
    verts,faces=mesh["vertices"],mesh["faces"]
    if not verts or not faces: raise ValueError("empty mesh")
    if not all(math.isfinite(c) for v in verts for c in v): raise ValueError("non-finite vertex")
    for f in faces:
        if len(f)!=3 or min(f)<0 or max(f)>=len(verts): raise ValueError("bad index")
    deg=0
    for a,b,c in faces:
        ab=_sub(verts[b],verts[a]); ac=_sub(verts[c],verts[a]); cr=_cross(ab,ac)
        if math.sqrt(_dot(cr,cr)) <= 1e-12: deg+=1
    if deg: raise ValueError(f"degenerate triangles: {deg}")
    mins=[min(v[i] for v in verts) for i in range(3)]
    maxs=[max(v[i] for v in verts) for i in range(3)]
    return {"vertex_count":len(verts),"triangle_count":len(faces),"degenerate_triangles":deg,"bounds_min":mins,"bounds_max":maxs}

def _project(v,view):
    if view=="front": return (v[0],v[2])
    if view=="side": return (v[1],v[2])
    if view=="top": return (v[0],v[1])
    raise ValueError(view)

def svg_wire(mesh, view, title):
    pts=[_project(v,view) for v in mesh["vertices"]]
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    mnx,mxx=min(xs),max(xs); mny,mxy=min(ys),max(ys)
    pad=.08; w,h=700,760
    sx=(w-100)/(max(mxx-mnx,1e-9)+2*pad); sy=(h-120)/(max(mxy-mny,1e-9)+2*pad); s=min(sx,sy)
    def cv(p): return 50+(p[0]-mnx+pad)*s, h-50-(p[1]-mny+pad)*s
    lines=[]; seen=set()
    for f in mesh["faces"]:
        for a,b in ((f[0],f[1]),(f[1],f[2]),(f[2],f[0])):
            e=tuple(sorted((a,b)))
            if e in seen: continue
            seen.add(e); x1,y1=cv(pts[a]); x2,y2=cv(pts[b])
            lines.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}"/>')
    return '\n'.join([f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">','<rect width="100%" height="100%" fill="white"/>',f'<text x="18" y="28" font-family="monospace" font-size="16">{title} / {view}</text>','<g stroke="black" stroke-width="0.8" fill="none" opacity="0.65">',*lines,'</g></svg>'])

def write_obj(mesh,path):
    p=Path(path); lines=["# AXM character organic form study"]
    for v in mesh["vertices"]: lines.append(f"v {v[0]:.9f} {v[1]:.9f} {v[2]:.9f}")
    for f in mesh["faces"]: lines.append("f "+" ".join(str(i+1) for i in f))
    p.write_text("\n".join(lines)+"\n",encoding="utf-8")

def build_evidence(out_dir):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    study=neutral_character_study(); form_metrics=validate_study(study); mesh=build_mesh(study); checks=mesh_checks(mesh)
    source_digest=canonical_digest(study); mesh_digest=canonical_digest({"vertices":mesh["vertices"],"faces":mesh["faces"],"regions":mesh["regions"]})
    (out/"source.json").write_text(json.dumps(study,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (out/"mesh.json").write_text(json.dumps(mesh,separators=(",",":"),sort_keys=True)+"\n",encoding="utf-8")
    write_obj(mesh,out/"character.obj")
    for view in ("front","side","top"): (out/f"{view}.svg").write_text(svg_wire(mesh,view,STUDY_ID),encoding="utf-8")
    receipt={
        "schema":"axm.character-organic-form-evidence/v0.1","study_id":STUDY_ID,"source_digest":source_digest,"mesh_digest":mesh_digest,
        "form_metrics":form_metrics,"mesh_checks":checks,
        "gates":{"source-validation":"PASS","bilateral-symmetry":"PASS","a-pose-angle":"PASS","finite-mesh":"PASS","bounded-indices":"PASS","nondegenerate-triangles":"PASS","flex-zones-truth-state":"PASS","donor-pass-inherited":False},
        "truth_boundary":["stylized human-like proportion study, not anatomy/biology validation","flex zones declared but not deformation tested","surfaces are disconnected form-study regions, not production skin topology","no rigging, animation, materials, runtime, gameplay, or CANON acceptance"],
    }
    (out/"evidence.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return receipt
