"""Batch ingest the top all-time most viewed Huberman Lab episodes.

Usage:
    python -m scripts.ingest_top_episodes               # Ingest top 50 (skips already indexed)
    python -m scripts.ingest_top_episodes --limit 15    # Ingest top 15
    python -m scripts.ingest_top_episodes --dry-run     # Preview status without making API calls
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from app.factory import get_chat_model, get_collection_name
from app.ingestion import (
    captions_to_segments,
    chunk_segments,
    fetch_raw_captions,
    fetch_video_title,
)
from app.vectorstore import get_vectorstore, index_chunks

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_top_episodes")

# Top 50 Huberman Lab episodes sorted by all-time views and citations
TOP_50_HUBERMAN_EPISODES: list[dict[str, str]] = [
    {"id": "nDLb8_wgX50", "title": "How to Build Immense Inner Strength | David Goggins"},
    {"id": "50BZQRT1dAg", "title": "A Process for Finding & Achieving Your Unique Purpose | Robert Greene"},
    {"id": "QmOF0crdyRU", "title": "Controlling Your Dopamine For Motivation, Focus & Satisfaction"},
    {"id": "hFL6qRIJZ_Y", "title": "ADHD & How Anyone Can Improve Their Focus"},
    {"id": "IAnhFUUCq6c", "title": "Dr. Andy Galpin: How to Build Strength, Muscle Size & Endurance"},
    {"id": "DkS1pkKpILY", "title": "What Alcohol Does to Your Body, Brain & Health"},
    {"id": "lIo9FcrljDk", "title": "Master Your Sleep & Be More Alert When Awake"},
    {"id": "Wcs2PFz5q6g", "title": "The Science of Making & Breaking Habits"},
    {"id": "DTCmprPCDqc", "title": "Dr. Peter Attia: Exercise, Nutrition, Hormones for Vitality & Longevity"},
    {"id": "ycOBZZeVeAc", "title": "Rick Rubin: How to Access Your Creativity"},
    {"id": "C0DMdUqF73Q", "title": "The Best Vitality & Health Protocols | Dr. Rhonda Patrick"},
    {"id": "K4Ze-Sp6aUE", "title": "The Science of Eating for Health, Fat Loss & Lean Muscle | Dr. Layne Norton"},
    {"id": "CD0bRU1e1ZM", "title": "Tools for Nutrition & Fitness | Dr. Layne Norton"},
    {"id": "-OBCwiPPfEU", "title": "Dr. Matthew Walker: The Biology of Sleep & Your Unique Sleep Needs"},
    {"id": "pq6WHJzOkno", "title": "Using Deliberate Cold Exposure for Health and Performance"},
    {"id": "9tRohh0gErM", "title": "Effects of Fasting & Time Restricted Eating on Fat Loss & Health"},
    {"id": "LG53Vxum0as", "title": "How to Focus to Change Your Brain (Neuroplasticity)"},
    {"id": "uXs-zPc63kM", "title": "Nicotine's Effects on the Brain & Body & How to Quit Smoking or Vaping"},
    {"id": "gXvuJu1kt48", "title": "The Effects of Cannabis (Marijuana) on the Brain & Body"},
    {"id": "qJXKhu5UZwk", "title": "The Science of How to Optimize Testosterone & Estrogen"},
    {"id": "oNkDA2F7CjM", "title": "Dr. Andy Galpin: How to Build Physical Endurance & Lose Fat"},
    {"id": "q37ARYnRDGc", "title": "Dr. Andy Galpin: Optimal Nutrition & Supplementation for Fitness"},
    {"id": "Ibj1k3IZTNU", "title": "How to Control Your Cortisol & Overcome Burnout"},
    {"id": "STAffeSFBVk", "title": "Optimal Morning & Evening Sunlight Routine | Dr. Andrew Huberman"},
    {"id": "at37Y8rKDlA", "title": "How to Optimize Your Water Quality & Intake for Health"},
    {"id": "gXkwXb99JpU", "title": "How to Breathe Correctly for Optimal Health, Mood, Learning & Performance"},
    {"id": "doupx8SAs5Y", "title": "Tim Ferriss: How to Learn Better & Create Your Best Future"},
    {"id": "VRvn3Oj5r3E", "title": "Lex Fridman: Machines, Creativity & Love"},
    {"id": "gbQFSMayJxk", "title": "Dr. Matthew Walker: The Science & Practice of Perfecting Your Sleep"},
    {"id": "n28W4AmvMDE", "title": "Dr. Robert Lustig: How Sugar, Fructose & Processed Food Affect Your Health"},
    {"id": "VAEzZeaV5zM", "title": "Controlling Sugar Cravings & Metabolism with Science-Based Tools"},
    {"id": "qPKd99Pa2iU", "title": "Dr. Paul Conti: How to Improve Your Mental Health"},
    {"id": "eMqWH3LYiII", "title": "Dr. Paul Conti: How to Build and Maintain Healthy Relationships"},
    {"id": "oUu3f0ETMJQ", "title": "Using Light (Sunlight, Blue Light & Red Light) to Optimize Health"},
    {"id": "juD99_sPWGU", "title": "Dr. Andy Galpin: Maximize Recovery to Achieve Fitness & Performance Goals"},
    {"id": "N5DAW8mkJ6Y", "title": "How to Enhance Your Immune System Function | Dr. Roger Seheult"},
    {"id": "ouCWNRvPk20", "title": "Optimize Your Gut Microbiome for Brain & Physical Health"},
    {"id": "vA50EK70whE", "title": "How to Optimize Drive, Motivation & Dopamine Baselines"},
    {"id": "EQ3GjpGq5Y8", "title": "Deliberate Heat & Sauna for Longevity, Heart Health & Growth Hormone"},
    {"id": "VRpCo8JEWwo", "title": "Using Caffeine to Optimize Mental & Physical Performance"},
    {"id": "ntfcfJ28eiU", "title": "Tools for Managing Stress & Anxiety in Real Time"},
    {"id": "U6dnOVth7-I", "title": "Science-Based Tools for Accelerating Learning & Memory"},
    {"id": "n9IxomBusuw", "title": "Dr. David Sinclair: The Biology of Slowing & Reversing Aging"},
    {"id": "Nmo4bxfFzM0", "title": "How to Optimize Thyroid & Metabolic Rate"},
    {"id": "wTBSGgbIvsY", "title": "How Meditation Works & Science-Based Effective Meditations"},
    {"id": "Xu1FMCxoEFc", "title": "Understanding & Conquering Depression"},
    {"id": "aQDOU3hPci0", "title": "Growth Mindset & How to Overcome Failure"},
    {"id": "XLr2RKoD-oY", "title": "Science of Muscle Hypertrophy & Training Frequency"},
    {"id": "dzOvi0Aa2EA", "title": "The Science & Process of Healing from Grief"},
    {"id": "E7W4OQfJWdw", "title": "Nutrients for Brain Health & Performance"},
]


def is_episode_indexed(video_id: str, active_collection: str) -> bool:
    """Check whether an episode is already in ChromaDB or local cache."""
    cache_file = Path("data/raw/huberman_lab") / f"{video_id}.json"
    if cache_file.exists():
        try:
            payload = json.loads(cache_file.read_text())
            cols = payload.get("indexed_collections", [])
            if isinstance(cols, list) and active_collection in cols:
                return True
        except Exception:
            pass

    try:
        vs = get_vectorstore()
        existing = vs.get(where={"episode_id": video_id}, limit=1, include=[])
        if existing and existing.get("ids"):
            return True
    except Exception:
        pass
    return False


def generate_episode_summary(title: str, transcript_sample: str) -> dict[str, Any]:
    """Generate concise episode summary, key takeaways, and search keywords."""
    prompt = f"""You are a scientific podcast archivist. Given this transcript sample from Dr. Andrew Huberman's episode titled "{title}", provide:
1. A 2-sentence executive summary.
2. 3 bullet points of core scientific takeaways.
3. 5 comma-separated indexing keywords.

Output valid JSON matching this exact structure:
{{
  "short_summary": "...",
  "key_takeaways": ["...", "...", "..."],
  "keywords": ["...", "...", "...", "...", "..."]
}}

Transcript sample:
{transcript_sample[:3500]}
"""
    try:
        model = get_chat_model()
        res = model.invoke(prompt)
        text = str(res.content).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        return {
            "short_summary": data.get("short_summary", ""),
            "key_takeaways": data.get("key_takeaways", []),
            "keywords": data.get("keywords", []),
        }
    except Exception as exc:
        logger.warning(f"Failed to generate structured summary: {exc}")
        return {
            "short_summary": f"Dr. Andrew Huberman explores the science and protocols of {title}.",
            "key_takeaways": ["Science-grounded protocols", "Actionable health tools", "Biological mechanisms"],
            "keywords": ["huberman", "neuroscience", "health", "protocols", "science"],
        }


def ingest_single_episode(video_id: str, fallback_title: str) -> bool:
    """Download captions, segment, chunk, embed, and index a single episode."""
    active_collection = get_collection_name()
    if is_episode_indexed(video_id, active_collection):
        logger.info(f"⏭️  Already indexed: {video_id} ({fallback_title})")
        return True

    cache_dir = Path("data/raw/huberman_lab")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{video_id}.json"

    raw_captions: list[dict[str, Any]] = []
    title = fallback_title

    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text())
            raw_captions = cached.get("captions", [])
            title = cached.get("title", fallback_title)
            logger.info(f"📦 Loaded {len(raw_captions)} cached caption lines for {video_id}")
        except Exception:
            raw_captions = []

    if not raw_captions:
        logger.info(f"🌐 Fetching live YouTube captions for {video_id}...")
        try:
            title = fetch_video_title(video_id) or fallback_title
        except Exception:
            title = fallback_title
        for attempt in range(1, 4):
            try:
                raw_captions = fetch_raw_captions(video_id)
                if raw_captions:
                    break
            except Exception as exc:
                err_str = str(exc)
                if "blocking requests from your IP" in err_str or "RequestBlocked" in type(exc).__name__:
                    logger.error(f"🛑 YouTube temporary IP rate-limit hit on {video_id}.")
                    return False
                if attempt < 3:
                    logger.warning(f"⚠️ Caption attempt {attempt} for {video_id} failed ({exc}). Retrying in 4s...")
                    time.sleep(4.0)
                else:
                    logger.error(f"❌ Failed to fetch captions for {video_id} after 3 attempts: {exc}")
                    return False

    # 1. Segment and chunk
    segments = captions_to_segments(
        raw_captions,
        show="huberman_lab",
        episode_id=video_id,
        episode_title=title,
        speaker="Andrew Huberman",
    )
    if not segments:
        logger.warning(f"⚠️ No valid speech segments for {video_id}")
        return False

    chunks = chunk_segments(segments, target_words=200, overlap_words=40)
    logger.info(f"🧩 Chunked {video_id} into {len(chunks)} blocks")

    # 2. Embed & Index into ChromaDB
    try:
        index_chunks(chunks)
        logger.info(f"💾 Vector store updated with {len(chunks)} chunks for {video_id}")
    except Exception as exc:
        logger.error(f"❌ Failed to index chunks into ChromaDB: {exc}")
        return False

    # 3. Generate summary & persist metadata cache
    sample_text = " ".join(c.text for c in chunks[:8])
    analysis = generate_episode_summary(title, sample_text)

    payload = {
        "show": "huberman_lab",
        "episode_id": video_id,
        "title": title,
        "speaker": "Andrew Huberman",
        "captions": raw_captions,
        "chunk_count": len(chunks),
        "short_summary": analysis["short_summary"],
        "key_takeaways": analysis["key_takeaways"],
        "keywords": analysis["keywords"],
        "indexed_collections": [active_collection],
    }
    cache_file.write_text(json.dumps(payload, indent=2))
    logger.info(f"✅ Successfully ingested & analyzed: {title}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest top Huberman Lab episodes sorted by views.")
    parser.add_argument("--limit", type=int, default=50, help="Number of episodes to ingest (1 to 50)")
    parser.add_argument("--dry-run", action="store_true", help="Inspect status without running ingestion")
    parser.add_argument(
        "--delay", type=float, default=5.0, help="Delay in seconds between episodes to avoid rate-limits"
    )
    args = parser.parse_args()

    episodes = TOP_50_HUBERMAN_EPISODES[: args.limit]
    active_collection = get_collection_name()

    print("\n=======================================================")
    print("🎙️  PodSeek Top Huberman Episodes Ingestion Pipeline")
    print(f"📊 Target Count: {len(episodes)} episodes | Active Chroma: '{active_collection}'")
    print("=======================================================\n")

    indexed_count = 0
    pending_count = 0

    for idx, ep in enumerate(episodes, 1):
        vid = ep["id"]
        title = ep["title"]
        already = is_episode_indexed(vid, active_collection)
        status_icon = "✓ Indexed" if already else "⏳ Pending"
        if already:
            indexed_count += 1
        else:
            pending_count += 1
        print(f"[{idx:02d}/50] {status_icon:<10} | {vid} | {title}")

    print(f"\nSummary: {indexed_count} already indexed, {pending_count} pending ingestion.")

    if args.dry_run:
        print("\n🔍 Dry-run completed. No API calls or downloads were made.")
        return 0

    if pending_count == 0:
        print("\n🎉 All requested episodes are already indexed in ChromaDB!")
        return 0

    print(f"\n🚀 Beginning ingestion for {pending_count} pending episodes...\n")

    success_count = 0
    failed_count = 0
    consecutive_blocks = 0

    for idx, ep in enumerate(episodes, 1):
        vid = ep["id"]
        title = ep["title"]
        if is_episode_indexed(vid, active_collection):
            continue

        print(f"\n--- [{idx}/{len(episodes)}] Processing: {title} ({vid}) ---")
        ok = ingest_single_episode(vid, title)
        if ok:
            success_count += 1
            consecutive_blocks = 0
        else:
            failed_count += 1
            consecutive_blocks += 1

        if consecutive_blocks >= 3:
            print("\n🛑 Pausing: YouTube's caption endpoint is temporarily throttling requests from this IP.")
            print("💡 Recommended solutions:")
            print("   1. Switch to your phone's mobile hotspot or another Wi-Fi network (takes effect immediately).")
            print("   2. Or wait 15–30 minutes for YouTube's rolling cooldown window to expire.")
            print("   3. Or export cookies from your browser to a 'cookies.txt' file in this folder.")
            break

        if idx < len(episodes):
            time.sleep(args.delay)

    print("\n=======================================================")
    print(
        f"🏁 Finished Ingestion: {success_count} succeeded, {failed_count} failed, {indexed_count} previously cached."
    )
    print("=======================================================\n")
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
