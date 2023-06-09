import pandas as pd
import transformers
import torch
from torch.nn import Dropout
from keras.preprocessing.sequence import pad_sequences
from torch.optim import Adam
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
from transformers import get_linear_schedule_with_warmup
from transformers import BertTokenizer, AdamW, BertModel
from torch import nn
from torch.nn import CrossEntropyLoss
import random

all_artists = pd.read_csv("artists-data.csv")
all_lyrics = pd.read_csv("lyrics-data.csv")
genre_number = {}
# for field_name in all_artists:
#  print(field_name)

artist_genre = {}
for i in range(len(all_artists['Link'])):
  artist_genre[all_artists['Link'][i]] = all_artists['Genre'][i]

for artist in all_artists['Link']:
#  print(artist)
  if artist in genre_number:
    genre_number[artist] += 1
  else:
    genre_number[artist] = 1

# for field_name in all_lyrics:
#  print(field_name)
  
english_all = all_lyrics[all_lyrics['Idiom']=="ENGLISH"]
temp = zip(english_all['Lyric'],english_all['ALink'])
retained = [(lyric, artist_genre[artist]) for lyric, artist in temp
            if artist in genre_number and genre_number[artist]==1]
single_genre_lyrics, associated_genre = zip(*retained)

print(len(single_genre_lyrics))
print(len(associated_genre))

single_genre_lyrics = []
associated_genre = []
for i in range(len(all_lyrics['ALink'])):
  if all_lyrics['Idiom'][i] == 'ENGLISH':
    current_artist = all_lyrics['ALink'][i]

    if current_artist in genre_number and genre_number[current_artist] == 1:
      single_genre_lyrics.append(all_lyrics['Lyric'][i])
      associated_genre.append(artist_genre[current_artist])

print(len(single_genre_lyrics))
print(len(associated_genre))

import random
temp = list(zip(single_genre_lyrics, associated_genre)) 
random.shuffle(temp) 
single_genre_lyrics, associated_genre = zip(*temp) 
print(single_genre_lyrics[0])
print(associated_genre[0])

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased', do_lower_case=True)
tokens = [tokenizer.encode(lyric) for lyric in single_genre_lyrics]
input_ids = pad_sequences(tokens, maxlen=200, dtype="long", value=0.0, truncating="post", padding="post")

genre_to_id = {}
count = 0
for i in all_artists['Genre']:
  if i not in genre_to_id:
    genre_to_id[i] = count
    count += 1
associated_genre_id = [genre_to_id[i] for i in associated_genre]

print(len(single_genre_lyrics))
print(len(associated_genre_id))
print(len(tokens))
print(len(input_ids))
attention_masks = [[float(i != 0.0) for i in ii] for ii in input_ids]
print(len(attention_masks))

#splittingdata
test_single = single_genre_lyrics[:9400]
dev_single = single_genre_lyrics[9400: 18800]
train_single = single_genre_lyrics[18800:]

test_genre = associated_genre_id[:9400]
dev_genre = associated_genre_id[9400: 18800]
train_genre = associated_genre[18800:]

test_input = input_ids[:9400]
dev_input = input_ids[9400: 18800]
train_input = input_ids[18800:]

test_masks = _iasks[:9400]
dev_masks = masks[9400: 18800]
train_masks = masks[18800:]

class Model(torch.nn.Module):
    def __init__(self,
                 model_name_or_path: str,
                 dropout: float,
                 num_genres: int):
        super(Model, self).__init__()
        self.bert_model = BertModel.from_pretrained(model_name_or_path)
        self.dropout = Dropout(dropout)
        self.num_genres = num_genres
        self.classifier = nn.Linear(self.bert_model.config.hidden_size, num_genres)

    def forward(self,
                input_ids: torch.tensor,
                attention_mask: torch.tensor,
                token_type_ids: torch.tensor,
                genre: torch.tensor = None
                ):
        last_hidden_states, pooler_output = self.bert_model(input_ids=input_ids,
                                                            attention_mask=attention_mask,
                                                            token_type_ids=token_type_ids)
        logits = self.classifier(self.dropout(pooler_output))

        loss_fct = CrossEntropyLoss()
        # Compute losses if labels provided
        if genre is not None:
            loss = loss_fct(logits.view(-1, self.num_genres), genre.type(torch.long))
        else:
            loss = torch.tensor(0)

        return logits, loss

train_data = TensorDataset(torch.tensor(train_input), torch.tensor(train_masks), torch.tensor(train_genre))
dev_data = TensorDataset(torch.tensor(dev_input), torch.tensor(dev_masks), torch.tensor(dev_genre))
test_data = TensorDataset(torch.tensor(test_input), torch.tensor(test_masks), torch.tensor(test_genre))

train_sampler = RandomSampler(train_data)
dev_sampler = SequentialSampler(dev_data)
test_sampler = SequentialSampler(test_data)

train_data_loader = DataLoader(train_data, sampler = train_sampler, batch_size = 16)
dev_data_loader = DataLoader(dev_data, sampler = dev_sampler, batch_size = 16)
test_data_loader = DataLoader(test_data, sampler = test_sampler, batch_size = 16)

model = Model('bert-base-uncased', 0.5, 6)

FULL_FINETUNING = True
if FULL_FINETUNING:
    param_optimizer = list(model.named_parameters())
    no_decay = ['bias', 'gamma', 'beta']
    optimizer_grouped_parameters = [
        {'params': [p for n, p in param_optimizer if not any(nd in n for nd in no_decay)],
         'weight_decay_rate': 0.01},
        {'params': [p for n, p in param_optimizer if any(nd in n for nd in no_decay)],
         'weight_decay_rate': 0.0}
    ]
else:
    param_optimizer = list(model.classifier.named_parameters())
    optimizer_grouped_parameters = [{"params": [p for n, p in param_optimizer]}]

optimizer = AdamW(
    optimizer_grouped_parameters,
    lr=5e-5,
    eps=1e-8
)

# Create the learning rate scheduler.
scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=40,
    num_training_steps= 10
)

for epoch in range(5):
  model.train()
  for batch in data_loader:
    input_ids, mask, genre = batch
    model.zero_grad()
    _, loss = model(input_ids, mask, None, genre)
    print(loss)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(parameters = model.parameters(), max_norm = 1.0)
    optimizer.step()
    scheduler.step()
