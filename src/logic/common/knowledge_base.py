"""Knowledge base service for loading and searching knowledge items."""

import logging
from pathlib import Path

from async_lru import alru_cache

from domain.entities import KnowledgeItem

logger = logging.getLogger(__name__)


@alru_cache(maxsize=128)
async def _load_knowledge_items_cached(kb_dir_str: str) -> tuple[KnowledgeItem, ...]:
    """Load all knowledge items with caching (module-level function).

    This is a module-level function so LRU cache works properly.
    Returns tuple instead of list for hashability (LRU cache requirement).

    Args:
        kb_dir_str: Knowledge base directory path as string (for hashability)

    Returns:
        tuple[KnowledgeItem, ...]: Cached knowledge items
    """
    kb_dir = Path(kb_dir_str)
    knowledge_items: list[KnowledgeItem] = []
    txt_files = list(kb_dir.glob("*.txt"))

    for txt_file in txt_files:
        try:
            content = txt_file.read_text(encoding="utf-8")
            knowledge_items.append(
                KnowledgeItem(
                    filename=txt_file.name,
                    content=content,
                )
            )
            logger.debug(f"Loaded knowledge file: {txt_file.name}")

        except Exception as e:
            logger.error(f"Error reading {txt_file.name}: {e}")
            continue

    return tuple(knowledge_items)


class KnowledgeBaseService:
    """Service for managing and searching the knowledge base."""

    def __init__(self, knowledge_base_dir: str) -> None:
        """Initialize knowledge base service.

        Args:
            knowledge_base_dir: Directory containing knowledge base .txt files
        """
        self.kb_dir = Path(knowledge_base_dir)
        self._ensure_kb_directory()
        logger.info(f"Knowledge base directory: {self.kb_dir}")

    def _ensure_kb_directory(self) -> None:
        """Ensure the knowledge base directory exists."""
        self.kb_dir.mkdir(parents=True, exist_ok=True)

    async def search(self, query: str) -> list[KnowledgeItem]:
        """Search knowledge base for relevant files.

        This is a simple implementation that loads all .txt files.
        The LLM will perform relevance filtering through natural language reasoning.
        Results are cached using async LRU cache for performance.

        Args:
            query: Search query (used for logging/context)

        Returns:
            list[KnowledgeItem]: List of knowledge items
        """
        logger.info(f"Searching knowledge base for: {query}")

        # Use async LRU cached function (handles empty directory check internally)
        cached_items = await _load_knowledge_items_cached(str(self.kb_dir))

        if not cached_items:
            logger.warning(f"No .txt files found in {self.kb_dir}")
            return []

        knowledge_items = list(cached_items)
        logger.info(f"Found {len(knowledge_items)} knowledge items")
        return knowledge_items

    async def get_all_filenames(self) -> list[str]:
        """Get list of all knowledge base filenames.

        Returns:
            list[str]: List of filenames
        """
        txt_files = list(self.kb_dir.glob("*.txt"))
        filenames = [f.name for f in txt_files]
        logger.info(f"Found {len(filenames)} knowledge files")
        return filenames

    async def get_by_filename(self, filename: str) -> KnowledgeItem | None:
        """Get a specific knowledge item by filename.

        Args:
            filename: Name of the file

        Returns:
            KnowledgeItem | None: Knowledge item if found, None otherwise
        """
        file_path = self.kb_dir / filename

        if not file_path.exists() or not file_path.is_file():
            logger.warning(f"Knowledge file not found: {filename}")
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            return KnowledgeItem(filename=filename, content=content)

        except Exception as e:
            logger.error(f"Error reading {filename}: {e}")
            return None
