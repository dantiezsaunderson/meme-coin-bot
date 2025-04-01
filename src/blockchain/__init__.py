"""
__init__.py for the blockchain module.

This module provides blockchain scanners for Ethereum and Solana.
"""
from .base import BlockchainScanner
from .ethereum import EthereumScanner
from .solana import SolanaScanner

# Factory function to get the appropriate scanner
def get_scanner(blockchain_type: str) -> BlockchainScanner:
    """
    Get a blockchain scanner for the specified blockchain type.
    
    Args:
        blockchain_type: The blockchain type ('ethereum' or 'solana').
        
    Returns:
        A BlockchainScanner instance.
        
    Raises:
        ValueError: If the blockchain type is not supported.
    """
    if blockchain_type.lower() == 'ethereum':
        return EthereumScanner()
    elif blockchain_type.lower() == 'solana':
        return SolanaScanner()
    else:
        raise ValueError(f"Unsupported blockchain type: {blockchain_type}")
