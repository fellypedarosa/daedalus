---
tags: [networking, physics, hardware]
date_created: 2026-04-12
source: "[[Introdução a Redes： Como Dados viram Ondas？ ｜ Parte 1]]"
---
# Modulation and Demodulation

To transport data across a physical medium (copper, air), discrete digital data (1s and 0s) must be transformed into continuous analog wave forms. 

## Mechanism
- **Modulation**: The process of manipulating a wave's properties (such as amplitude and frequency) to encode binary data.
- **Demodulation**: The reverse process of reading the incoming analog wave and interpreting its fluctuations back into digital bits.
- **Modems**: The hardware device that performs this conversion natively gets its name from this process (**Mo**dulator-**Dem**odulator).

## Multiplexing
A single physical cable can carry multiple signals simultaneously by separating them into different frequency channels (a subset of multiplexing). For example, ancient ADSL modems worked alongside landline phones because human voice only occupies `0 to 4 KHz`, leaving the cable's upper frequencies completely free for data transmission.
