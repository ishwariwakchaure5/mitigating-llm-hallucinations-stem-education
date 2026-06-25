import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.claim_decomposer import ClaimDecomposer
from app.services.equation_store import EquationStore

cd = ClaimDecomposer()

# Claim 5: plain-text "F = m/a"
units5 = cd.decompose(
    "Newton's second law states that force equals mass divided by acceleration F = m/a"
)
print("[5] units:", [(u.unit_type, u.latex_equations) for u in units5])

# Claim 6: "PV = nRT"
units6 = cd.decompose(
    "The ideal gas law is PV = nRT where R is the universal gas constant 8.314 J per mol per Kelvin"
)
print("[6] units:", [(u.unit_type, u.latex_equations) for u in units6])

es = EquationStore()
for expr in ["F = m/a", "F = m*a", "PV = nRT"]:
    r = es.latex_to_sympy(expr)
    print(f"  latex_to_sympy({expr!r}) -> {r}  type={type(r).__name__}")

print()
print("Threshold test: claim[4] entail=0.61, cosine_top=0.89")
e = 0.61 * 0.70 + 0.89 * 0.30
print(f"  blended={e:.3f}  verdict={'correct' if e > 0.45 else 'uncertain'}")

print("Threshold test: claim[6] entail=0.60, cosine_top=0.79")
e2 = 0.60 * 0.70 + 0.79 * 0.30
print(f"  blended={e2:.3f}  verdict={'correct' if e2 > 0.45 else 'uncertain'}")
