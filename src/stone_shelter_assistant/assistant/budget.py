from dataclasses import dataclass
from decimal import Decimal


@dataclass
class RunBudget:
    spent: Decimal = Decimal("0")
    reserved: Decimal = Decimal("0")

    def try_reserve(self, amount: Decimal) -> bool:
        # TODO: Check the monthly application and user budgets before each OpenRouter call.
        # Reserve the estimated cost and settle it against the actual charge from OpenRouter.
        return True

    def settle(self, amount: Decimal, actual_cost: Decimal) -> None:
        self.reserved -= amount
        self.spent += actual_cost
