from src.main import app
from src.adapters.erp_input import _TRANSFORMS
from src.adapters.tms_output import _WRITEBACKS

print("ERP transforms:", list(_TRANSFORMS.keys()))
print("TMS adapters:", list(_WRITEBACKS.keys()))
erp = [r.path for r in app.routes if hasattr(r, "path") and "erp" in r.path]
print("ERP route:", erp)
print("All OK")
