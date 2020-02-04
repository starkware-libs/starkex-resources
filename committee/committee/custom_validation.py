from starkware.objects.availability import StateUpdate


async def is_valid(state_update: StateUpdate) -> bool:
    """
    A hook for third parties to validate the state_update before signing the new root.
    """
    return True
