"""
Actividad 2: genera las figuras del documento Actividad2_Comparaciones.pdf y verifica sus valores.

Reproduce el circuito N-Grover (n = 2, estado 01) y el de la sección 2.2 del tutorial de IBM,
compara estados y conteos (AerSimulator, semilla 2026) y guarda en ../figuras:
  - hist_tutorial_vs_ngrover.pdf
  - hist_iteraciones.pdf

Uso (desde la carpeta docs):  python generar_figuras_actividad2.py
"""
import numpy as np, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.quantum_info import Statevector, Operator
from qiskit_aer import AerSimulator
OUT = sys.argv[1] if len(sys.argv) > 1 else "../figuras"

n = 2; MarkState = '01'
def Oracle(qc, target_state):
    n = len(target_state)
    for i, bit in enumerate(reversed(target_state)):
        if bit == '0': qc.x(i)
    qc.h(n-1); qc.mcx(list(range(n-1)), n-1); qc.h(n-1)
    for i, bit in enumerate(reversed(target_state)):
        if bit == '0': qc.x(i)
def diffusion_operator(circuit):
    circuit.h(range(n)); circuit.barrier(); circuit.x(range(n)); circuit.barrier()
    circuit.h(n-1); circuit.mcx(list(range(n-1)), n-1); circuit.h(n-1); circuit.barrier()
    circuit.x(range(n)); circuit.barrier(); circuit.h(range(n))
# exact folder-2 notebook circuit
g = QuantumCircuit(n); g.h(range(n)); g.barrier()
g.barrier(); Oracle(g, MarkState)
g.barrier(); g.barrier(); diffusion_operator(g)
g.barrier()
sv = Statevector(g); print("SV N-Grover:", np.round(sv.data.real, 4))

# tutorial
def initialization(circuit):
    n = circuit.num_qubits
    for q in range(n-1): circuit.h(q)
    circuit.x(n-1); circuit.h(n-1); circuit.barrier(); return circuit
def oracle(circuit):
    circuit.x(1); circuit.ccx(0,1,2); circuit.x(1); circuit.barrier()
def diffusion(circuit):
    iq = circuit.num_qubits-1
    circuit.h(range(iq)); circuit.x(range(iq)); circuit.h(iq-1)
    circuit.mcx(list(range(iq-1)), iq-1); circuit.h(iq-1); circuit.x(range(iq)); circuit.h(range(iq)); circuit.barrier()
t = QuantumCircuit(QuantumRegister(2,"q"), QuantumRegister(1,"ancillary"), ClassicalRegister(3,"meas"))
initialization(t); oracle(t); diffusion(t); t.h(2); t.x(2)
t_nm = t.copy(); t.measure_all(add_bits=False)
print("SV tutorial:", np.round(Statevector(t_nm.remove_final_measurements(inplace=False)).data.real,4))

backend = AerSimulator(seed_simulator=2026)
gm = g.copy(); gm.measure_all()
isa_g = transpile(gm, backend, optimization_level=1); isa_t = transpile(t, backend, optimization_level=1)
c_ng = backend.run(isa_g, shots=1024).result().get_counts()
c_tu = backend.run(isa_t, shots=1024).result().get_counts()
print("counts NG", c_ng, "counts tut", c_tu)
for nm, qc, isa in [("Tut", t, isa_t), ("NG", gm, isa_g)]:
    ops = {k:v for k,v in qc.count_ops().items() if k not in ("barrier","measure")}
    print(nm, "qubits", qc.num_qubits, "depth", qc.depth(lambda x: x.operation.name not in ("barrier",)), "depth(raw)", qc.depth(), ops)
    print("   transp depth", isa.depth(), dict(isa.count_ops()))
# toffoli cost on generic basis
tof = QuantumCircuit(3); tof.ccx(0,1,2)
print("CCX -> cx count:", transpile(tof, basis_gates=['cx','rz','sx','x'], optimization_level=1).count_ops())
o2 = QuantumCircuit(2); Oracle(o2, '01')
print("NG oracle -> ", transpile(o2, basis_gates=['cx','rz','sx','x'], optimization_level=1).count_ops())
o3 = QuantumCircuit(3); oracle(o3)
print("Tut oracle ->", transpile(o3, basis_gates=['cx','rz','sx','x'], optimization_level=1).count_ops())

# iterations
theta = np.arcsin(1/2)
it_counts = {}
for k in range(4):
    qc = QuantumCircuit(n); qc.h(range(n))
    for _ in range(k): Oracle(qc, MarkState); diffusion_operator(qc)
    s = Statevector(qc); print("k",k, np.round(s.data.real,3), s.probabilities()[1], np.sin((2*k+1)*theta)**2)
    if k in (1,2):
        qm = qc.copy(); qm.measure_all()
        it_counts[k] = backend.run(transpile(qm, backend), shots=1024).result().get_counts()
print("iter counts", it_counts)
try:
    p = QuantumCircuit(n); Oracle(p, '011')
except Exception as e: print("ERR", type(e).__name__, e)

# Figures
plt.rcParams.update({"font.size": 10, "font.family": "serif"})
labels = ['00','01','10','11']
fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.0))
tut_labels = [f"{i:03b}" for i in range(8)]
axs[0].bar(tut_labels, [c_tu.get(l,0) for l in tut_labels], color="#6c8ebf")
axs[0].set_title("Tutorial de IBM (3 qubits: $a\\,q_1q_0$)"); axs[0].set_ylabel("Conteos (1024 disparos)")
axs[1].bar(labels, [c_ng.get(l,0) for l in labels], color="#d79b00")
axs[1].set_title("N-Grover, $n=2$ ($q_1q_0$)")
for ax in axs:
    ax.set_ylim(0, 1150); ax.set_xlabel("Resultado medido")
    for p_ in ax.patches:
        if p_.get_height()>0: ax.annotate(f"{int(p_.get_height())}", (p_.get_x()+p_.get_width()/2, p_.get_height()+15), ha="center", fontsize=9)
    ax.spines[['top','right']].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/hist_tutorial_vs_ngrover.pdf"); plt.close(fig)

fig, ax = plt.subplots(figsize=(6, 3.0)); w=0.38; x=np.arange(4)
b1=ax.bar(x-w/2, [it_counts[1].get(l,0) for l in labels], w, label="1 iteración", color="#d79b00")
b2=ax.bar(x+w/2, [it_counts[2].get(l,0) for l in labels], w, label="2 iteraciones", color="#82b366")
ax.set_xticks(x, labels); ax.set_ylim(0,1150); ax.set_xlabel("Resultado medido $q_1q_0$"); ax.set_ylabel("Conteos (1024 disparos)")
for b in list(b1)+list(b2):
    if b.get_height()>0: ax.annotate(f"{int(b.get_height())}", (b.get_x()+b.get_width()/2, b.get_height()+15), ha="center", fontsize=8)
ax.legend(frameon=False); ax.spines[['top','right']].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/hist_iteraciones.pdf"); plt.close(fig)
print("figs ok")
