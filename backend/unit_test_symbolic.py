"""
Verify end-to-end symbolic contradiction detection:
  KB equation: $F = ma$   → Eq(F, a*m)
  Claim:       F = m/a    → Eq(F, m/a)
  Expected:    match = contradiction
"""
import sys, os, shutil, pathlib
sys.path.insert(0, os.path.dirname(__file__))

from app.services.equation_store import EquationStore
from app.services.chunker import Chunk

KB_ID = "test-symbolic-fix"

# Clean up leftover graph
eq_dir = pathlib.Path("uploads") / KB_ID
shutil.rmtree(eq_dir, ignore_errors=True)

# Simulate a chunk that has the KB equation $F = ma$
chunk = Chunk(
    chunk_id="c1",
    document_id="d1",
    kb_id=KB_ID,
    text="Newton second law: $F = ma$",
    page_number=1,
    chunk_index=0,
    has_equations=True,
    equation_strings=["$F = ma$"],
)

es = EquationStore()
indexed = es.extract_and_index([chunk], KB_ID)
print(f"Indexed equations: {indexed}")

# Now query with the wrong version from claim [5]
result = es.find(KB_ID, "F = m/a")
print(f"find('F = m/a'): {result}")
assert result["match"] == "contradiction", f"Expected contradiction, got: {result}"

# Verify correct claim still gives exact or no match (not contradiction)
result2 = es.find(KB_ID, "F = m*a")
print(f"find('F = m*a'): {result2}")
# Might be exact (if canonical hash matches) or none — but NOT contradiction
assert result2["match"] != "contradiction", f"Should not be contradiction: {result2}"

print()
print("ALL SYMBOLIC CHECKS PASSED")
shutil.rmtree(eq_dir, ignore_errors=True)
