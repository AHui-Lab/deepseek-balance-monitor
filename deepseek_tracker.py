import os, json
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
USAGE_FILE = os.path.join(BASE, "deepseek_usage.json")

# Pricing per 1M tokens (CNY) – read from deepseek_config.json
def _get_pricing():
    cfg_path = os.path.join(BASE, "deepseek_config.json")
    try:
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
            model = cfg.get("model", "deepseek-chat")
            p = cfg.get("pricing", {}).get(model, {})
            return (p.get("input", 1.0), p.get("output", 2.0), p.get("cache_hit", 0.1))
    except:
        pass
    return (1.0, 2.0, 0.1)

PRICE_INPUT, PRICE_OUTPUT, PRICE_CACHE_HIT = _get_pricing()


def _load():
    try:
        if os.path.exists(USAGE_FILE):
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}


def _save(data):
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_usage(prompt_tokens=0, completion_tokens=0,
                 cache_hit_tokens=0, cache_miss_tokens=0):
    """Call this after each DeepSeek API call to log usage.

    Pass the values from the response body's `usage` field:
      - prompt_tokens
      - completion_tokens
      - prompt_cache_hit_tokens
      - prompt_cache_miss_tokens
    """
    today = date.today().isoformat()
    data = _load()
    if today not in data:
        data[today] = {
            "requests": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cache_hit_tokens": 0,
            "cache_miss_tokens": 0,
        }
    day = data[today]
    day["requests"] += 1
    day["prompt_tokens"] += prompt_tokens
    day["completion_tokens"] += completion_tokens
    day["total_tokens"] += prompt_tokens + completion_tokens
    day["cache_hit_tokens"] += cache_hit_tokens
    day["cache_miss_tokens"] += cache_miss_tokens
    _save(data)
    return day


def get_monthly_stats():
    today = date.today().isoformat()
    data = _load()
    day = data.get(today, {})
    tokens = day.get("month_tokens", 0)
    reqs = day.get("month_requests", 0)
    cost = day.get("month_cost", 0)
    balance = day.get("balance", 0)
    if tokens == 0:
        return None
    return {
        "requests": reqs,
        "total_tokens": tokens,
        "cost_total": cost,
        "balance": balance,
    }

def get_today_stats():
    return get_monthly_stats()
    global PRICE_INPUT, PRICE_OUTPUT, PRICE_CACHE_HIT
    PRICE_INPUT, PRICE_OUTPUT, PRICE_CACHE_HIT = _get_pricing()
    """Return today's accumulated usage stats, or None."""
    today = date.today().isoformat()
    data = _load()
    day = data.get(today)
    if not day:
        return None
    prompt = day["prompt_tokens"]
    completion = day["completion_tokens"]
    total = day["total_tokens"]
    hit = day["cache_hit_tokens"]
    miss = day["cache_miss_tokens"]
    cache_total = hit + miss
    hit_rate = hit / cache_total if cache_total > 0 else 0.0

    # Cost calculation
    non_cache_input = miss  # tokens that missed cache cost full price
    cache_input = hit       # tokens that hit cache cost discounted price
    cost_input = (non_cache_input * PRICE_INPUT + cache_input * PRICE_CACHE_HIT) / 1_000_000
    cost_output = completion * PRICE_OUTPUT / 1_000_000
    cost_total = cost_input + cost_output

    return {
        "requests": day["requests"],
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "cache_hit_tokens": hit,
        "cache_miss_tokens": miss,
        "hit_rate": hit_rate,
        "cost_input": round(cost_input, 6),
        "cost_output": round(cost_output, 6),
        "cost_total": round(cost_total, 6),
    }
