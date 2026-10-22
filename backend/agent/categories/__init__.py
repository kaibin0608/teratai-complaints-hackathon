"""Category handlers. Import this package to register all handlers."""
from .atm import ATMHandler  # noqa: F401
from .duplicate import DuplicateChargeHandler  # noqa: F401
from .failed_transfer import FailedTransferHandler  # noqa: F401
from .fee import FeeDisputeHandler  # noqa: F401
from .scam import ScamTransferHandler  # noqa: F401
from .service import ServiceQualityHandler  # noqa: F401
from .unauthorised import UnauthorisedCardHandler  # noqa: F401
