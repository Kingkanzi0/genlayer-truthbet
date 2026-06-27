# TruthBet — Self-Resolving Prediction Market

An Intelligent Contract on GenLayer that lets users bet GEN on a 
yes/no real-world question. When resolved, the contract fetches a 
live web page and uses an LLM to judge the outcome — all validators 
must agree (Equivalence Principle) before the result is accepted 
on-chain. Winners can then claim their proportional share of the pool.

## Deployment

- **Network:** GenLayer Bradbury Testnet
- **Contract Address:** `0x92A5F2008505411De615A34c4b43cC49C40C0944`
- **Transaction Hash:** `0xdb01a780bf60f0a6451ccef4042325296387f0addc1549f814a5963d8ebc12e2`
- **Explorer:** https://explorer-bradbury.genlayer.com/address/0x92A5F2008505411De615A34c4b43cC49C40C0944

## How it works

- `bet_yes()` / `bet_no()` — place a GEN bet on either outcome
- `resolve()` — fetches the resolution URL, asks an LLM to judge the 
  outcome based on the page content, requires validator consensus
- `claim()` — winners withdraw their stake plus a share of the losing pool
