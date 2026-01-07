# train_layout.py
import torch
from torch.utils.data import Dataset
from transformers import T5Tokenizer, T5ForConditionalGeneration, Trainer, TrainingArguments
import json

# --- [1. 데이터셋 정의] ---
class LayoutDataset(Dataset):
    def __init__(self, tokenizer, data, max_len=64):
        self.tokenizer = tokenizer
        self.data = data
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        item = self.data[index]
        
        # 입력: 문맥 정보
        # 예: "generate layout: mood: Elegant, pos: Left"
        source_text = f"generate layout: category: {item.get('category', 'General')}, mood: {item['mood']}, pos: {item['pos']}"
        
        # 정답(Target): 좌표 문자열
        # 예: "title_x:10 title_y:10 title_w:80..." (실수 대신 정수로 변환 권장)
        target_text = (
            f"title_x:{item['layout']['title']['x']} "
            f"title_y:{item['layout']['title']['y']} "
            f"body_x:{item['layout']['body']['x']} "
            f"body_y:{item['layout']['body']['y']}"
        )

        source = self.tokenizer(
            source_text, 
            max_length=self.max_len, 
            padding="max_length", 
            truncation=True, 
            return_tensors="pt"
        )
        target = self.tokenizer(
            target_text, 
            max_length=self.max_len, 
            padding="max_length", 
            truncation=True, 
            return_tensors="pt"
        )

        return {
            "input_ids": source.input_ids.squeeze(),
            "attention_mask": source.attention_mask.squeeze(),
            "labels": target.input_ids.squeeze()
        }

# --- [2. 학습 실행 함수] ---
def train():
    # 예시 학습 데이터 (실제로는 수천 개 필요)
    dummy_data = [
        {
            "mood": "Elegant", "pos": "Left",
            "layout": {"title": {"x": 60, "y": 10}, "body": {"x": 60, "y": 40}}
        },
        {
            "mood": "Energetic", "pos": "Center",
            "layout": {"title": {"x": 5, "y": 5}, "body": {"x": 5, "y": 80}}
        }
    ] * 50 # 데이터 뻥튀기

    tokenizer = T5Tokenizer.from_pretrained("t5-small")
    model = T5ForConditionalGeneration.from_pretrained("t5-small")

    dataset = LayoutDataset(tokenizer, dummy_data)

    args = TrainingArguments(
        output_dir="./layout_model_results",
        num_train_epochs=5,
        per_device_train_batch_size=4,
        save_steps=100,
        save_total_limit=2,
        logging_dir="./logs",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
    )

    print("🚀 학습 시작...")
    trainer.train()
    
    # 모델 저장
    model.save_pretrained("./layout_model_checkpoint")
    tokenizer.save_pretrained("./layout_model_checkpoint")
    print("✅ 모델 저장 완료: ./layout_model_checkpoint")

if __name__ == "__main__":
    train()