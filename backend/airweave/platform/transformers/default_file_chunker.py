"""Default file transformer."""

from airweave.core.logging import logger
from airweave.platform.decorators import transformer
from airweave.platform.entities._base import ChunkEntity, FileEntity, ParentEntity
from airweave.platform.file_handling.async_markitdown import markitdown


@transformer(name="File Chunker")
async def file_chunker(file: FileEntity) -> list[ParentEntity | ChunkEntity]:
    """Default file chunker that converts files to markdown chunks.

    This transformer:
    1. Takes a FileEntity as input
    2. Converts the file to markdown using AsyncMarkItDown
    3. Splits the markdown into logical chunks
    4. Yields each chunk as a ChunkEntity

    Args:
        file: The FileEntity to process

    Returns:
        list[ParentEntity | ChunkEntity]: The processed chunks
    """
    file_class = type(file)
    produced_entities = []

    # Get the specific parent/child models for this file entity type
    FileParentClass, FileChunkClass = file_class.create_parent_chunk_models()

    if not file.local_path:
        logger.error(f"File {file.name} has no local path")
        return

    try:
        # Convert file to markdown
        result = await markitdown.convert(file.local_path)

        if not result or not result.text_content:
            logger.warning(f"No content extracted from file {file.name}")
            return

        # Split content into chunks and yield as child entities
        chunks = _split_into_chunks(result.text_content)

        # Create parent entity for the file using all fields from original entity
        file_data = file.model_dump()
        file_data.update(
            {
                "number_of_chunks": len(chunks),
            }
        )
        parent = FileParentClass(**file_data)
        produced_entities.append(parent)

        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            chunk = FileChunkClass(
                name=f"{file.name} - Chunk {i + 1}",
                entity_id=file.entity_id,
                sync_id=file.sync_id,
                parent_entity_id=parent.entity_id,
                parent_db_entity_id=parent.db_entity_id,
                md_content=chunk,
                md_type="text",
                md_position=i,
                md_parent_title=file.name,
                metadata={
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )
            produced_entities.append(chunk)

    except Exception as e:
        logger.error(f"Error processing file {file.name}: {str(e)}")
        raise e

    return produced_entities


def _split_by_headers(content: str, max_chunk_size: int) -> list[str]:
    """Split content by headers only when necessary due to size constraints."""
    if not content.strip():
        return []

    # If content is already small enough, return it as a single chunk
    if len(content) <= max_chunk_size:
        return [content]

    # Otherwise, split at major headers (# or ##) when needed
    chunks = []
    lines = content.split("\n")
    current_chunk = []
    current_size = 0

    for line in lines:
        line_size = len(line) + 1  # +1 for newline

        # Only split at major headers (# or ##) when the chunk is getting large
        is_major_header = line.startswith("# ") or line.startswith("## ")
        should_split = is_major_header and current_size > max_chunk_size * 0.5 and current_size > 0

        # Always split if we've exceeded the max size
        if current_size + line_size > max_chunk_size:
            should_split = True

        if should_split and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_size = 0

        current_chunk.append(line)
        current_size += line_size

    # Add the final chunk
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def _split_into_chunks(content: str, max_chunk_size: int = 5000) -> list[str]:  # noqa: C901
    """Split content into chunks, trying to preserve semantic coherence.

    This function is deliberately conservative about splitting, preferring to keep
    related content together when possible.
    """
    if not content.strip():
        return []

    # If content is small enough, return it as a single chunk
    if len(content) <= max_chunk_size:
        return [content]

    # Try to split by headers first
    chunks = _split_by_headers(content, max_chunk_size)

    # If we still have chunks that are too large, split them further
    final_chunks = []

    for chunk in chunks:
        if len(chunk) <= max_chunk_size:
            final_chunks.append(chunk)
            continue

        # For oversized chunks, split by paragraphs as a last resort
        paragraphs = []
        current_para = []
        is_in_code_block = False

        # Identify paragraphs while preserving code blocks
        for line in chunk.split("\n"):
            # Track code block state
            if line.strip().startswith("```"):
                is_in_code_block = not is_in_code_block

            # Only create paragraph breaks when not in a code block
            if not line.strip() and not is_in_code_block and current_para:
                paragraphs.append("\n".join(current_para))
                current_para = []
                continue

            current_para.append(line)

        # Add the last paragraph
        if current_para:
            paragraphs.append("\n".join(current_para))

        # Create chunks from paragraphs, being conservative about splitting
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para) + 2  # +2 for paragraph separator

            # If adding this paragraph would exceed the limit, start a new chunk
            if current_size + para_size > max_chunk_size and current_chunk:
                final_chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_size = 0

            # If a single paragraph is too large, we have no choice but to include it as is
            if para_size > max_chunk_size:
                if current_chunk:
                    final_chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_size = 0
                final_chunks.append(para)
                continue

            current_chunk.append(para)
            current_size += para_size

        # Add the final chunk
        if current_chunk:
            final_chunks.append("\n\n".join(current_chunk))

    return final_chunks
