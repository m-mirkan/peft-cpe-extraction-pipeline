import argparse
import json
import os
import torch

# Disable torch.compile / dynamo warnings on Windows where Triton is not installed
torch._dynamo.config.disable = True
torch._dynamo.config.suppress_errors = True

import outlines
from transformers import AutoModelForCausalLM, AutoTokenizer

from cpe_resolver import CPEDictionaryResolver, TOEExtraction
from generate_synthetic_dataset import SYSTEM_PROMPT


def load_model_for_inference(base_model_id: str, lora_dir: str = None):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if (device == "cuda" and torch.cuda.is_bf16_supported()) else torch.float16

    print(f"[Infer] Loading base model `{base_model_id}` on {device} ({dtype})...")
    tokenizer = AutoTokenizer.from_pretrained(lora_dir if (lora_dir and os.path.exists(lora_dir)) else base_model_id)
    hf_model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=dtype,
        device_map="auto" if device == "cuda" else None,
    )

    if lora_dir and os.path.exists(lora_dir):
        from peft import PeftModel
        print(f"[Infer] Attaching fine-tuned LoRA adapter from `{lora_dir}`...")
        hf_model = PeftModel.from_pretrained(hf_model, lora_dir)
        hf_model = hf_model.merge_and_unload()

    hf_model.eval()
    return outlines.from_transformers(hf_model, tokenizer)


def main():
    parser = argparse.ArgumentParser(description="Run TOE extraction + CPE dictionary resolution")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--lora_dir", type=str, default="checkpoints/qwen25_3b_cpe_lora")
    parser.add_argument("--input_file", type=str, default="data/benchmarks/names.json", help="Path to names.json or reverse_benchmark_dict.json")
    parser.add_argument("--limit", type=int, default=10, help="Number of benchmark entries to run")
    parser.add_argument("--offset", type=int, default=0, help="Starting index in input_file")
    parser.add_argument("--output_file", type=str, default="outputs/benchmark_predictions.json")
    parser.add_argument("--attach_fw_to_models", action="store_true", help="Also emit model_firmware CPEs per hardware unit")
    parser.add_argument("--reprocess_only", type=str, default=None, help="Re-run CPE resolver on an existing predictions JSON without loading LLM")
    args = parser.parse_args()

    resolver = CPEDictionaryResolver()

    if args.reprocess_only:
        with open(args.reprocess_only, "r", encoding="utf-8") as f:
            saved = json.load(f)
        for item in saved:
            parsed = TOEExtraction.model_validate(item["extracted_structure"])
            cpes = resolver.build_cpes_from_extraction(
                parsed,
                attach_shared_firmware_to_models=args.attach_fw_to_models,
                raw_source_text=item["input"],
            )
            item["cpes"] = cpes
            print(f"\n[{item['index']}] INPUT: {item['input']}")
            for c in cpes:
                print(f"  {c['short']:50s} [{c['resolution']}]")
        with open(args.reprocess_only, "w", encoding="utf-8") as f:
            json.dump(saved, f, indent=2, ensure_ascii=False)
        return

    with open(args.input_file, "r", encoding="utf-8") as f:
        entries = json.load(f)

    subset = entries[args.offset : args.offset + args.limit]
    model = load_model_for_inference(args.base_model, args.lora_dir)

    all_outputs = []
    for i, raw_text in enumerate(subset, start=args.offset + 1):
        prompt = (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f'<|im_start|>user\nExtract from: "{raw_text}"<|im_end|>\n'
            f"<|im_start|>assistant\n"
        )

        try:
            raw_json = model(prompt, TOEExtraction, max_new_tokens=2048)
            if isinstance(raw_json, str):
                parsed = TOEExtraction.model_validate_json(raw_json)
            else:
                parsed = raw_json
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:300]}"
            print(f"\n[{i}] FAILED: {raw_text}\n  {err}")
            all_outputs.append({"index": i, "input": raw_text, "error": err, "extracted_structure": None, "cpes": []})
            continue

        cpes = resolver.build_cpes_from_extraction(
            parsed,
            attach_shared_firmware_to_models=args.attach_fw_to_models,
            raw_source_text=raw_text,
        )

        print(f"\n{'='*75}\n[{i}] INPUT: {raw_text}\n{'-'*75}")
        for item in cpes:
            print(f"  {item['short']:50s} [{item['resolution']}]")

        all_outputs.append(
            {
                "index": i,
                "input": raw_text,
                "extracted_structure": parsed.model_dump(),
                "cpes": cpes,
            }
        )
        os.makedirs(os.path.dirname(args.output_file) or ".", exist_ok=True)
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(all_outputs, f, indent=2, ensure_ascii=False)

    out_dir = os.path.dirname(args.output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(all_outputs, f, indent=2, ensure_ascii=False)
    print(f"\n[Infer] Saved {len(all_outputs)} structured predictions + CPEs to `{args.output_file}`.")


if __name__ == "__main__":
    main()
