import io
import uuid
import logging
from typing import List
from PIL import Image
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from app.config import settings
from app.services.document_parser import ParsedDocument

logger = logging.getLogger(__name__)

# Module-level singletons — loaded once per process
_clip_model = None
_clip_processor = None


def get_clip():
    """Return (CLIPModel, CLIPProcessor), downloading on first call (~600 MB)."""
    global _clip_model, _clip_processor
    if _clip_model is None:
        logger.info("Loading CLIP ViT-B/32 model (first time: downloads ~600 MB)...")
        import torch
        from transformers import CLIPModel, CLIPProcessor

        _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        _clip_model.eval()
        logger.info("CLIP loaded.")
    return _clip_model, _clip_processor


class VisualStore:
    EMBED_DIM = 512

    def __init__(self) -> None:
        self.qdrant = QdrantClient(
            host=settings.qdrant_host, port=settings.qdrant_port
        )

    # ── collection management ─────────────────────────────────────────────────

    def ensure_collection(self, kb_id: str) -> str:
        name = f"vera_{kb_id}_visual"
        existing = {c.name for c in self.qdrant.get_collections().collections}
        if name not in existing:
            self.qdrant.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=self.EMBED_DIM, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant visual collection: %s", name)
        return name

    # ── embedding helpers ─────────────────────────────────────────────────────

    def embed_image(self, image: Image.Image) -> List[float]:
        import torch
        import torch.nn.functional as F

        model, processor = get_clip()
        inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            # Call vision_model + visual_projection directly to avoid API
            # differences across transformers versions (get_image_features may
            # return a ModelOutput instead of a plain tensor in some releases).
            vision_out = model.vision_model(pixel_values=inputs["pixel_values"])
            features   = model.visual_projection(vision_out.pooler_output)
            features   = F.normalize(features, dim=-1)
        return features[0].tolist()

    def embed_text(self, text: str) -> List[float]:
        import torch
        import torch.nn.functional as F

        model, processor = get_clip()
        # CLIP text encoder has a 77-token limit
        inputs = processor(
            text=[text[:77]], return_tensors="pt", padding=True, truncation=True
        )
        with torch.no_grad():
            text_out = model.text_model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
            )
            features = model.text_projection(text_out.pooler_output)
            features = F.normalize(features, dim=-1)
        return features[0].tolist()

    # ── indexing ──────────────────────────────────────────────────────────────

    def index_visuals(self, parsed: ParsedDocument, kb_id: str) -> int:
        """Embed and upsert all image blocks into the visual Qdrant collection."""
        if not parsed.image_blocks:
            return 0

        collection = self.ensure_collection(kb_id)
        count = 0
        for block in parsed.image_blocks:
            try:
                img = Image.open(io.BytesIO(block.image_bytes)).convert("RGB")
                # Skip tiny icons / decorative elements
                if img.width < 60 or img.height < 60:
                    continue
                vec = self.embed_image(img)
                self.qdrant.upsert(
                    collection_name=collection,
                    points=[
                        PointStruct(
                            id=str(uuid.uuid4()),
                            vector=vec,
                            payload={
                                "document_id": parsed.document_id,
                                "kb_id": kb_id,
                                "page_number": block.page_number,
                                "caption": block.caption,
                            },
                        )
                    ],
                )
                count += 1
            except Exception as e:
                logger.warning("Failed to index image on page %d: %s", block.page_number, e)

        logger.info("Indexed %d visuals for document %s", count, parsed.document_id)
        return count

    # ── retrieval ─────────────────────────────────────────────────────────────

    def search_by_text(
        self, text: str, kb_id: str, top_k: int = 5
    ) -> List[dict]:
        """Find images most similar to a text query using CLIP cross-modal search."""
        vec = self.embed_text(text)
        results = self.qdrant.search(
            collection_name=f"vera_{kb_id}_visual",
            query_vector=vec,
            limit=top_k,
            with_payload=True,
        )
        return [{"score": r.score, **r.payload} for r in results]
