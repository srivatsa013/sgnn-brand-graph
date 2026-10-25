# Formal task specification

Frozen with `configs/phase0.json` on 2026-10-11. This file defines the predictive task. Hypothesis tests on the same shifts are defined in `reports/pre_registration.md`.

## 1. One supervised example

An example is one sentiment event. The event is a triple (entity s, source q, day t0) accepted by the event rule. The label source is q. The other source may appear in the features. It does not appear in the label.

The graph snapshot G(t0) has:

- Node set V: the knowledge-graph nodes, including s.
- Structural edges frozen from the dated Wikidata or DBpedia snapshot. They do not depend on t0.
- Co-mention edges counted only from documents whose timestamp is on or before t0-8, and on or after t0-187, so the lookback is 180 days ending at t0-8. An undirected co-mention edge exists when the document count is at least 3. Its weight is log(1 + count). It has no balance-theory sign.

Positive relations, sign +1, one shared parameter matrix W_pos: parent organization, subsidiary, owned by, owner of, brand, product, manufacturer. Stored once as undirected, implemented as two arcs.

Competitor arcs are directed and have sign -1. The incoming direction and the outgoing direction use different parameter matrices, W_comp_in and W_comp_out. A missing reverse arc is a missing arc, not a zero-weight copy.

## 2. Features

For every node i and the history days t0-7 through t0-1, each source contributes:

- the bin sentiment, with a missing bin filled by 0
- a mask that is 1 when the bin was observed and 0 when it was missing
- log(1 + mention count)

Filling a missing feature with 0 is allowed only beside that mask. The label is never filled.

Also, for the same source as the label and for the other source separately: baseline mean, baseline sample standard deviation, and log(1 + baseline mention count) on t0-28 through t0-1.

Node type is a one-hot vector with entries brand, parent, product, competitor, ceo, other.

Two shock features are nonzero only on s: the event-bin sentiment of source q, and the surprise z of that event. Every node also has an indicator that is 1 only on s.

No feature may use a document dated t0 or later, except the two shock features on s, which use the event bin of s by definition. Target nodes do not receive s's post-window text.

Features are standardized with means and variances computed on the training fold only. The scaler is stored with the fold.

## 3. Labels

For each one-hop structural neighbor j of s, the label is

delta(j, q) = mean of source-q sentiment on t0 through t0+7, minus the mean on t0-7 through t0-1.

Both means use the shift rule: at least 3 observed bins in each window, and every document that mentions s is removed first. If either window fails, j is masked out of the loss. The event node s is not a label. Control entities are not labels. A neighbor connected only by a co-mention edge is not a primary label.

The masked set for an event can be empty. That event is dropped from the loss and counted.

## 4. Model

The signed model is a balance-theory message-passing network in the sense of Derr, Ma, and Tang (2018), small enough for these graphs. Hidden size, depth, and dropout are chosen only on validation from the grid hidden in {32, 64}, layers in {1, 2}, dropout in {0.0, 0.2}. Learning rate is 0.001, weight decay is 0.0001, maximum epochs 200, patience 20 on validation MAE.

Let h_i be the input features of node i.

When the depth is 1, the layer keeps a positive channel and a negative channel, plus a co-mention channel that is not given a sign:

- positive channel: self features and the mean of W_pos applied to positive neighbors
- negative channel: self features and the mean of W_comp_in on incoming competitor neighbors, plus the mean of W_comp_out on outgoing competitor neighbors
- co-mention channel: the mean of W_co applied to co-mention neighbors, with the log-count weight, and no sign flip

When the depth is 2, the second layer follows balance theory. A two-step walk is balanced when the product of its structural signs is +1, and unbalanced when the product is -1. The second layer aggregates the first-layer states along balanced walks into one channel and along unbalanced walks into another. Co-mention edges never enter those walks. They stay on their own channel.

The prediction is a linear head on the concatenation of the structural channels and the co-mention channel. It outputs one number, the predicted delta.

Activation after each channel is ReLU. Empty neighborhoods contribute a zero vector, not a missing row.

## 5. Loss and metrics

Training loss is the Huber loss with delta 0.5, averaged over unmasked neighbor labels. Selection metric is validation MAE. Reported test metrics are MAE, RMSE, and sign accuracy of the predicted shift. Sign accuracy ignores labels whose true shift is exactly 0, and the ignore count is reported.

Metrics are computed per event, then averaged across events with equal event weight, so an event with more neighbors does not dominate. Across seeds 0, 1, 2, 3, and 4, report the mean and the standard deviation of the event-weighted metric.

## 6. Baselines

Each learned baseline uses the same grid, the same seeds, the same folds, and the same early-stopping rule.

- No-graph: the same head on the node's own features. No messages.
- Unsigned GCN: every structural edge is treated as positive and undirected, with one shared structural matrix. Co-mention remains its own type. Competitor direction is erased.
- Sign-shuffled: the signed model on a graph that permutes structural signs while keeping the sign counts.
- Degree-matched random: the signed model on a configuration-model structural graph with the same degrees and the same sign counts.
- Linear diffusion: closed form, so it has no architecture search. On the training fold only, fit one coefficient alpha by least squares: predicted delta of j equals alpha times edge sign times the source shock z. This baseline is not given extra features or extra search iterations.

Primary comparisons are signed versus unsigned, and signed versus no-graph. The other three are secondary.

FinBERT is not one of these graph baselines. Phase 3 scores the hand-labeled brand-domain sample with FinBERT and with the entity-aware classifier and reports both. That comparison does not detect events.

## 7. Leakage checks that must pass before any test metric is trusted

For every evaluated event at t0:

1. Every co-mention document has timestamp on or before t0-8.
2. Every history feature, other than the two shock features on s, uses dates on or before t0-1.
3. No label document is used as a feature of any node.
4. Every training event has an earlier t0 than every test event in a chronological split.
5. The training loss does not contain a test-event label.
6. Scaler statistics do not use validation or test rows.

A failure of any check is a pipeline failure. The metrics are not interpretable until the check passes. H3 is not decided in the phase that builds the model. It is decided only on the held-out events after the leakage check has passed.

## 8. What this task is not

It is not link-sign prediction, the original SGCN benchmark. It is not stock-return prediction. It does not train on control entities. It does not pool news and social labels into one regression target.
