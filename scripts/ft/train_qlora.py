"""QLoRA Qwen2.5-3B Wilmercito (Unsloth). Solo de noche, server detenido.

Uso:
    ~/ft-wilmercito/venv/bin/python scripts/ft/train_qlora.py \
        --data ~/ft-wilmercito/data/ft_train.jsonl \
        --out ~/ft-wilmercito/outputs/wilmercito-3b-r1 \
        [--epochs 1] [--max-steps 10]
"""

import argparse

PROMPT = """Below is an instruction. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--max-steps", type=int, default=0)
    args = ap.parse_args()

    from datasets import load_dataset
    from trl import SFTTrainer, SFTConfig
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-3B-Instruct-bnb-4bit",
        max_seq_length=2048,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model, r=16, lora_alpha=16,
        lora_dropout=0, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth",
    )

    def fmt(ex):
        sys, user, asst = (m["content"] for m in ex["messages"])
        return {"text": PROMPT.format(sys, user, asst)}

    ds = load_dataset("json", data_files=args.data, split="train").map(fmt)
    cfg = SFTConfig(
        dataset_text_field="text",
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps or -1,
        learning_rate=2e-4,
        output_dir=args.out,
        save_total_limit=1,
    )
    SFTTrainer(model=model, tokenizer=tokenizer, train_dataset=ds, args=cfg).train()
    model.save_pretrained(args.out)
    print("ADAPTER_OK", args.out)


if __name__ == "__main__":
    main()
