import argparse
import json
import os
import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training


class ChatMLCompletionDataset(Dataset):
    """
    Tokenizes ChatML examples and masks loss (-100) on the system + user prompt
    so Qwen 2.5 3B only computes cross-entropy loss on the target assistant JSON tokens.
    """

    def __init__(self, jsonl_path: str, tokenizer, max_length: int = 1024):
        self.samples = []
        self.tokenizer = tokenizer
        self.max_length = max_length

        assistant_marker = "<|im_start|>assistant\n"

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                full_text = rec["text"]

                idx = full_text.find(assistant_marker)
                if idx == -1:
                    continue

                prompt_part = full_text[: idx + len(assistant_marker)]
                prompt_ids = tokenizer.encode(prompt_part, add_special_tokens=False)
                full_ids = tokenizer.encode(full_text, add_special_tokens=False, truncation=True, max_length=max_length)

                if len(full_ids) <= len(prompt_ids):
                    continue

                labels = [-100] * len(prompt_ids) + full_ids[len(prompt_ids) :]
                self.samples.append({"input_ids": full_ids, "labels": labels})

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


def collate_chatml_batch(batch, pad_token_id: int):
    max_len = max(len(x["input_ids"]) for x in batch)
    input_ids = []
    attention_mask = []
    labels = []

    for x in batch:
        pad_len = max_len - len(x["input_ids"])
        input_ids.append(x["input_ids"] + [pad_token_id] * pad_len)
        attention_mask.append([1] * len(x["input_ids"]) + [0] * pad_len)
        labels.append(x["labels"] + [-100] * pad_len)

    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Qwen2.5-3B-Instruct on Synthetic Compound TOE JSON")
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--train_file", type=str, default="data/synthetic/synthetic_train.jsonl")
    parser.add_argument("--val_file", type=str, default="data/synthetic/synthetic_val.jsonl")
    parser.add_argument("--output_dir", type=str, default="checkpoints/qwen25_3b_cpe_lora")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--grad_accum", type=int, default=8)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--max_length", type=int, default=1024)
    parser.add_argument("--max_steps", type=int, default=-1, help="Set >0 for a quick smoke test")
    args = parser.parse_args()

    print(f"[Train] Loading tokenizer & 4-bit QLoRA model: {args.model_id}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    train_ds = ChatMLCompletionDataset(args.train_file, tokenizer, max_length=args.max_length)
    val_ds = ChatMLCompletionDataset(args.val_file, tokenizer, max_length=args.max_length)
    print(f"[Train] Loaded {len(train_ds)} train samples, {len(val_ds)} val samples.")

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_steps=15,
        logging_steps=5,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="no",
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        optim="adamw_8bit",
        report_to="none",
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=lambda b: collate_chatml_batch(b, tokenizer.pad_token_id),
    )

    print("[Train] Starting QLoRA fine-tuning...")
    trainer.train()

    os.makedirs(args.output_dir, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"[Train] Saved fine-tuned LoRA adapter to: {args.output_dir}")


if __name__ == "__main__":
    main()
