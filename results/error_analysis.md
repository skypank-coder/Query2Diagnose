# Error analysis: `q2d` in run `20261029T170525Z`

663 of 1350 dialogues end with the wrong action. Buckets are checked in the order below; each failure counts once.

| Cause | Failures | Share |
|---|---|---|
| misparsed_negation | 0 | 0% |
| missed_codemixed_token | 110 | 17% |
| wrong_clarification | 164 | 25% |
| retrieval_miss | 33 | 5% |
| premature_stop | 14 | 2% |
| hypothesis_model_gap | 342 | 52% |

## missed_codemixed_token

- **c0001-codemixed_hi** (codemixed_hi): "fridge bilkul thanda nahi kar raha, aas paas kaafi jagah hai, the dial is turned to the lowest cooling, kahin paani nahi hai"
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.7189, 6 turns, turn_budget)
  - normalised: "fridge completely cold not doing, aas near kaafi space is, the dial is turned to the lowest cooling, anywhere water not is"
  - interpretation p=0.375: `{"compartment_affected": "fridge", "placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_cold"}`
  - interpretation p=0.125: `{"compartment_affected": "fridge", "primary_symptom": "not_cooling", "thermostat_setting": "too_cold"}`
  - t=0 clarification `thermostat_setting`: "Just to check I understood: where is the temperature knob or setting - warm side, middle, or coldest?" -> "Warm side / lowest cooling" (parsed `too_warm`, meant `too_warm`; H_L=2.4056, H_D=3.5815)
  - t=1 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "There is no fan inside" (parsed `not_applicable`, meant `not_applicable`; H_L=1.7023, H_D=2.9933)
  - t=2 clarification `placement_clearance`: "Just to check I understood: is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Plenty of space and shade" (parsed `adequate`, meant `adequate`; H_L=1.6725, H_D=2.5772)
  - t=3 diagnostic `condenser_coils_dusty`: "Are the coils at the back or underneath covered in dust or lint?" -> "No, they look clean" (parsed `no`, meant `no`; H_L=1.5513, H_D=2.4683)
  - t=4 diagnostic `door_seal_condition`: "Does the door close and seal properly? Is the rubber gasket torn or is there a gap?" -> "Seals fine" (parsed `good`, meant `good`; H_L=1.5353, H_D=2.2946)
  - t=5 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=1.5178, H_D=2.1083)
- **c0001-codemixed_hi** (codemixed_hi): "fridge bilkul thanda nahi kar raha, aas paas kaafi jagah hai, the dial is turned to the lowest cooling, kahin paani nahi hai"
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.4191, 6 turns, turn_budget)
  - normalised: "fridge completely cold not doing, aas near kaafi space is, the dial is turned to the lowest cooling, anywhere water not is"
  - interpretation p=0.25: `{"compartment_affected": "fridge", "primary_symptom": "not_cooling"}`
  - interpretation p=0.25: `{"compartment_affected": "fridge", "primary_symptom": "not_cooling", "thermostat_setting": "too_cold"}`
  - t=0 clarification `thermostat_setting`: "Just to check I understood: where is the temperature knob or setting - warm side, middle, or coldest?" -> "Warm side / lowest cooling" (parsed `not_sure`, meant `too_warm`; H_L=2.25, H_D=3.6768)
  - t=1 diagnostic `noise_type`: "What kind of sound does it make?" -> "Just the usual soft hum" (parsed `normal_hum`, meant `normal_hum`; H_L=2.25, H_D=3.6768)
  - t=2 clarification `placement_clearance`: "Just to check I understood: is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Plenty of space and shade" (parsed `adequate`, meant `adequate`; H_L=1.9793, H_D=3.4607)
  - t=3 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "There is no fan inside" (parsed `not_applicable`, meant `not_applicable`; H_L=1.9874, H_D=3.3591)
  - t=4 diagnostic `condenser_coils_dusty`: "Are the coils at the back or underneath covered in dust or lint?" -> "No, they look clean" (parsed `no`, meant `no`; H_L=1.9841, H_D=3.0661)
  - t=5 diagnostic `door_seal_condition`: "Does the door close and seal properly? Is the rubber gasket torn or is there a gap?" -> "Seals fine" (parsed `good`, meant `good`; H_L=1.9852, H_D=2.9517)
- **c0001-codemixed_hi** (codemixed_hi): "fridge bilkul thanda nahi kar raha, aas paas kaafi jagah hai, the dial is turned to the lowest cooling, kahin paani nahi hai"
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.7072, 6 turns, turn_budget)
  - normalised: "fridge completely cold not doing, aas near kaafi space is, the dial is turned to the lowest cooling, anywhere water not is"
  - interpretation p=0.5: `{"compartment_affected": "fridge", "placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_cold"}`
  - interpretation p=0.25: `{"compartment_affected": "fridge", "primary_symptom": "not_cooling"}`
  - t=0 clarification `thermostat_setting`: "Just to check I understood: where is the temperature knob or setting - warm side, middle, or coldest?" -> "Warm side / lowest cooling" (parsed `too_warm`, meant `too_warm`; H_L=1.75, H_D=3.5859)
  - t=1 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "There is no fan inside" (parsed `not_applicable`, meant `not_applicable`; H_L=1.3189, H_D=3.0682)
  - t=2 diagnostic `placement_clearance`: "Is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Plenty of space and shade" (parsed `adequate`, meant `adequate`; H_L=1.2804, H_D=2.6704)
  - t=3 diagnostic `condenser_coils_dusty`: "Are the coils at the back or underneath covered in dust or lint?" -> "No, they look clean" (parsed `no`, meant `no`; H_L=1.3503, H_D=2.5239)
  - t=4 diagnostic `door_seal_condition`: "Does the door close and seal properly? Is the rubber gasket torn or is there a gap?" -> "Seals fine" (parsed `good`, meant `good`; H_L=1.3353, H_D=2.3536)
  - t=5 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=1.3189, H_D=2.1706)

## wrong_clarification

- **c0001-clean** (clean): "It has stopped cooling properly. There is no water anywhere, the temperature knob is on the warmest setting and it has plenty of space around it."
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.6351, 6 turns, turn_budget)
  - normalised: "It has stopped cooling properly. There is no water anywhere, the temperature knob is on the warmest setting and it has plenty of space around it."
  - interpretation p=0.5: `{"placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm", "water_leak_location": "none"}`
  - interpretation p=0.25: `{"placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm"}`
  - t=0 clarification `compartment_affected`: "Just to check I understood: which part has the problem - the fridge section, the freezer, or both?" -> "Fridge section" (parsed `not_sure`, meant `fridge`; H_L=1.75, H_D=3.3103)
  - t=1 diagnostic `noise_type`: "What kind of sound does it make?" -> "Just the usual soft hum" (parsed `normal_hum`, meant `normal_hum`; H_L=1.75, H_D=3.3103)
  - t=2 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=1.3646, H_D=2.9168)
  - t=3 diagnostic `condenser_coils_dusty`: "Are the coils at the back or underneath covered in dust or lint?" -> "No, they look clean" (parsed `no`, meant `no`; H_L=1.3709, H_D=2.6128)
  - t=4 clarification `water_leak_location`: "Just to check I understood: do you see water anywhere - inside at the bottom, or under the fridge?" -> "No water" (parsed `none`, meant `none`; H_L=1.3639, H_D=2.438)
  - t=5 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "There is no fan inside" (parsed `not_applicable`, meant `not_applicable`; H_L=1.2988, H_D=2.4415)
- **c0001-incomplete** (incomplete): "The cooling is very weak. There is no water anywhere."
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.4605, 6 turns, turn_budget)
  - normalised: "The cooling is very weak. There is no water anywhere."
  - interpretation p=0.375: `{"primary_symptom": "not_cooling"}`
  - interpretation p=0.375: `{"primary_symptom": "not_cooling", "water_leak_location": "none"}`
  - t=0 clarification `compartment_affected`: "Just to check I understood: which part has the problem - the fridge section, the freezer, or both?" -> "Fridge section" (parsed `not_sure`, meant `fridge`; H_L=1.8113, H_D=3.8134)
  - t=1 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "There is no fan inside" (parsed `not_applicable`, meant `not_applicable`; H_L=1.8113, H_D=3.8134)
  - t=2 diagnostic `placement_clearance`: "Is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Plenty of space and shade" (parsed `adequate`, meant `adequate`; H_L=1.8088, H_D=3.6274)
  - t=3 diagnostic `thermostat_setting`: "Where is the temperature knob or setting - warm side, middle, or coldest?" -> "Warm side / lowest cooling" (parsed `too_warm`, meant `too_warm`; H_L=1.8146, H_D=3.5768)
  - t=4 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=1.7316, H_D=3.1221)
  - t=5 diagnostic `condenser_coils_dusty`: "Are the coils at the back or underneath covered in dust or lint?" -> "No, they look clean" (parsed `no`, meant `no`; H_L=1.7427, H_D=2.898)
- **c0001-spelling** (spelling): "It has stopped cooling priperly. There is no water anywherd, thee temperature knob is on the waarmest stting and it has plenty of space aorund it."
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.5762, 6 turns, turn_budget)
  - normalised: "It has stopped cooling properly. There is no water anywhere, fine temperature knob is on the warmest setting and it has plenty of space around it."
  - interpretation p=0.375: `{"placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm"}`
  - interpretation p=0.25: `{"placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm", "water_leak_location": "none"}`
  - t=0 clarification `compartment_affected`: "Just to check I understood: which part has the problem - the fridge section, the freezer, or both?" -> "Fridge section" (parsed `not_sure`, meant `fridge`; H_L=1.9056, H_D=3.5354)
  - t=1 clarification `thermostat_setting`: "Just to check I understood: where is the temperature knob or setting - warm side, middle, or coldest?" -> "Warm side / lowest cooling" (parsed `too_warm`, meant `too_warm`; H_L=1.9056, H_D=3.5354)
  - t=2 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "There is no fan inside" (parsed `not_applicable`, meant `not_applicable`; H_L=1.7103, H_D=3.3683)
  - t=3 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=1.6945, H_D=3.0562)
  - t=4 diagnostic `condenser_coils_dusty`: "Are the coils at the back or underneath covered in dust or lint?" -> "No, they look clean" (parsed `no`, meant `no`; H_L=1.7046, H_D=2.8265)
  - t=5 diagnostic `condenser_fan_running`: "At the lower back, next to the compressor, is the small fan spinning while the compressor runs?" -> "There is no fan there" (parsed `not_applicable`, meant `not_applicable`; H_L=1.7033, H_D=2.6751)

## retrieval_miss

- **c0179-clean** (clean): "Thick frost keeps forming on the walls in the freezer. The door closes properly and the motor at the back is humming."
  - gold fault `excess_frost_manual_defrost`, gold action `excess_frost_manual_defrost`; predicted `REFER` (top `excess_frost_manual_defrost`, p=0.8899, 5 turns, unsupported)
  - normalised: "Thick frost keeps forming on the walls in the freezer. The door closes properly and the motor at the back is humming."
  - interpretation p=0.375: `{"compartment_affected": "freezer", "compressor_running": "yes", "noise_location": "back_bottom", "noise_type": "normal_hum", "primary_symptom": "frost_buildup"}`
  - interpretation p=0.25: `{"compartment_affected": "freezer", "compressor_running": "yes", "door_seal_condition": "good", "frost_on_back_wall": "yes", "noise_location": "back_bottom", "noise_type": "normal_hum", "primary_symptom": "frost_buildup"}`
  - t=0 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=2.1556, H_D=2.2876)
  - t=1 clarification `door_seal_condition`: "Just to check I understood: does the door close and seal properly? Is the rubber gasket torn or is there a gap?" -> "Seals fine" (parsed `good`, meant `good`; H_L=2.1611, H_D=1.6095)
  - t=2 clarification `frost_on_back_wall`: "Just to check I understood: is there frost or ice on the back wall inside the freezer or fridge?" -> "Yes, there is frost" (parsed `yes`, meant `yes`; H_L=2.151, H_D=1.3113)
  - t=3 diagnostic `vents_blocked_or_overloaded`: "Is the fridge packed full, or is food blocking the air vents inside?" -> "No, there is space" (parsed `no`, meant `no`; H_L=2.1119, H_D=0.9184)
  - t=4 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "There is no fan inside" (parsed `not_applicable`, meant `not_applicable`; H_L=2.1111, H_D=0.8013)
- **c0210-clean** (clean): "The fridge will not turn on at all. The fan inside the freezer is not running."
  - gold fault `power_supply`, gold action `power_supply`; predicted `REFER` (top `power_supply`, p=0.9735, 4 turns, unsupported)
  - normalised: "The fridge will not turn on at all. The fan inside the freezer is not running."
  - interpretation p=0.25: `{"compartment_affected": "both", "compressor_running": "no", "evaporator_fan_running": "no", "primary_symptom": "not_powering_on"}`
  - interpretation p=0.25: `{"compartment_affected": "both", "evaporator_fan_running": "no", "primary_symptom": "not_powering_on"}`
  - t=0 clarification `compartment_affected`: "Just to check I understood: which part has the problem - the fridge section, the freezer, or both?" -> "Both" (parsed `both`, meant `both`; H_L=2.5, H_D=1.2429)
  - t=1 clarification `power_supply_ok`: "Just to check I understood: when you open the door, does the light inside come on (or the display light up)?" -> "No light at all" (parsed `no`, meant `no`; H_L=2.1514, H_D=1.0952)
  - t=2 clarification `compressor_running`: "Just to check I understood: is the compressor (the motor at the lower back) running? You can usually hear a hum or feel it vibrate." -> "No, it is silent" (parsed `no`, meant `no`; H_L=2.1207, H_D=0.4598)
  - t=3 diagnostic `condenser_fan_running`: "At the lower back, next to the compressor, is the small fan spinning while the compressor runs?" -> "No, it is not spinning" (parsed `no`, meant `no`; H_L=2.1051, H_D=0.354)
- **c0210-codemixed_hi** (codemixed_hi): "fridge chalu hi nahi ho raha, freezer ke andar fan nahi chal raha"
  - gold fault `power_supply`, gold action `power_supply`; predicted `REFER` (top `power_supply`, p=0.9762, 5 turns, unsupported)
  - normalised: "fridge switched on hi not is happening, freezer ke inside fan not running"
  - interpretation p=0.25: `{"compartment_affected": "fridge", "evaporator_fan_running": "no", "primary_symptom": "not_powering_on"}`
  - interpretation p=0.125: `{"compartment_affected": "fridge", "primary_symptom": "not_powering_on"}`
  - t=0 clarification `compartment_affected`: "Just to check I understood: which part has the problem - the fridge section, the freezer, or both?" -> "Both" (parsed `both`, meant `both`; H_L=2.75, H_D=1.6247)
  - t=1 clarification `power_supply_ok`: "Just to check I understood: when you open the door, does the light inside come on (or the display light up)?" -> "No light at all" (parsed `no`, meant `no`; H_L=1.8506, H_D=0.8238)
  - t=2 clarification `evaporator_fan_running`: "Just to check I understood: open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "No, it does not run" (parsed `no`, meant `no`; H_L=1.7826, H_D=0.4831)
  - t=3 clarification `compressor_running`: "Just to check I understood: is the compressor (the motor at the lower back) running? You can usually hear a hum or feel it vibrate." -> "No, it is silent" (parsed `no`, meant `no`; H_L=1.7754, H_D=0.3776)
  - t=4 diagnostic `condenser_fan_running`: "At the lower back, next to the compressor, is the small fan spinning while the compressor runs?" -> "No, it is not spinning" (parsed `no`, meant `no`; H_L=1.7548, H_D=0.3084)

## premature_stop

- **c0166-clean** (clean): "The walls are covered in frost in the freezer. It is not overloaded, there is frost on the back wall inside and it has plenty of space around it."
  - gold fault `excess_frost_manual_defrost`, gold action `REFER`; predicted `excess_frost_manual_defrost` (top `excess_frost_manual_defrost`, p=0.8064, 1 turns, confident_and_supported)
  - normalised: "The walls are covered in frost in the freezer. It is not overloaded, there is frost on the back wall inside and it has plenty of space around it."
  - interpretation p=0.75: `{"compartment_affected": "freezer", "frost_on_back_wall": "yes", "placement_clearance": "adequate", "primary_symptom": "frost_buildup", "vents_blocked_or_overloaded": "no"}`
  - interpretation p=0.25: `{"compartment_affected": "freezer", "frost_on_back_wall": "yes", "placement_clearance": "adequate", "primary_symptom": "frost_buildup"}`
  - t=0 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=0.8113, H_D=1.8966)
- **c0166-clean** (clean): "The walls are covered in frost in the freezer. It is not overloaded, there is frost on the back wall inside and it has plenty of space around it."
  - gold fault `excess_frost_manual_defrost`, gold action `REFER`; predicted `excess_frost_manual_defrost` (top `excess_frost_manual_defrost`, p=0.8141, 1 turns, confident_and_supported)
  - normalised: "The walls are covered in frost in the freezer. It is not overloaded, there is frost on the back wall inside and it has plenty of space around it."
  - interpretation p=0.875: `{"compartment_affected": "freezer", "frost_on_back_wall": "yes", "placement_clearance": "adequate", "primary_symptom": "frost_buildup", "vents_blocked_or_overloaded": "no"}`
  - interpretation p=0.125: `{"compartment_affected": "freezer", "frost_on_back_wall": "yes", "placement_clearance": "adequate", "primary_symptom": "frost_buildup"}`
  - t=0 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=0.5436, H_D=1.8783)
- **c0166-clean** (clean): "The walls are covered in frost in the freezer. It is not overloaded, there is frost on the back wall inside and it has plenty of space around it."
  - gold fault `excess_frost_manual_defrost`, gold action `REFER`; predicted `excess_frost_manual_defrost` (top `excess_frost_manual_defrost`, p=0.796, 1 turns, confident_and_supported)
  - normalised: "The walls are covered in frost in the freezer. It is not overloaded, there is frost on the back wall inside and it has plenty of space around it."
  - interpretation p=0.875: `{"compartment_affected": "freezer", "frost_on_back_wall": "yes", "placement_clearance": "adequate", "primary_symptom": "frost_buildup", "vents_blocked_or_overloaded": "no"}`
  - interpretation p=0.125: `{"compartment_affected": "freezer", "primary_symptom": "frost_buildup"}`
  - t=0 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=0.5436, H_D=1.9724)

## hypothesis_model_gap

- **c0001-clean** (clean): "It has stopped cooling properly. There is no water anywhere, the temperature knob is on the warmest setting and it has plenty of space around it."
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.7397, 6 turns, turn_budget)
  - normalised: "It has stopped cooling properly. There is no water anywhere, the temperature knob is on the warmest setting and it has plenty of space around it."
  - interpretation p=0.75: `{"placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm", "water_leak_location": "none"}`
  - interpretation p=0.25: `{"placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm"}`
  - t=0 diagnostic `compartment_affected`: "Which part has the problem - the fridge section, the freezer, or both?" -> "Fridge section" (parsed `fridge`, meant `fridge`; H_L=0.8113, H_D=3.1963)
  - t=1 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "There is no fan inside" (parsed `not_applicable`, meant `not_applicable`; H_L=0.8112, H_D=2.824)
  - t=2 diagnostic `condenser_coils_dusty`: "Are the coils at the back or underneath covered in dust or lint?" -> "No, they look clean" (parsed `no`, meant `no`; H_L=0.8116, H_D=2.366)
  - t=3 diagnostic `door_seal_condition`: "Does the door close and seal properly? Is the rubber gasket torn or is there a gap?" -> "Seals fine" (parsed `good`, meant `good`; H_L=0.8118, H_D=2.1906)
  - t=4 clarification `water_leak_location`: "Just to check I understood: do you see water anywhere - inside at the bottom, or under the fridge?" -> "No water" (parsed `none`, meant `none`; H_L=0.812, H_D=2.0038)
  - t=5 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=0.6857, H_D=1.9936)
- **c0001-clean** (clean): "It has stopped cooling properly. There is no water anywhere, the temperature knob is on the warmest setting and it has plenty of space around it."
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.7397, 6 turns, turn_budget)
  - normalised: "It has stopped cooling properly. There is no water anywhere, the temperature knob is on the warmest setting and it has plenty of space around it."
  - interpretation p=0.625: `{"placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm", "water_leak_location": "none"}`
  - interpretation p=0.375: `{"placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm"}`
  - t=0 diagnostic `compartment_affected`: "Which part has the problem - the fridge section, the freezer, or both?" -> "Fridge section" (parsed `fridge`, meant `fridge`; H_L=0.9544, H_D=3.1994)
  - t=1 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "There is no fan inside" (parsed `not_applicable`, meant `not_applicable`; H_L=0.9544, H_D=2.8273)
  - t=2 clarification `water_leak_location`: "Just to check I understood: do you see water anywhere - inside at the bottom, or under the fridge?" -> "No water" (parsed `none`, meant `none`; H_L=0.9546, H_D=2.3703)
  - t=3 diagnostic `condenser_coils_dusty`: "Are the coils at the back or underneath covered in dust or lint?" -> "No, they look clean" (parsed `no`, meant `no`; H_L=0.8645, H_D=2.3575)
  - t=4 diagnostic `door_seal_condition`: "Does the door close and seal properly? Is the rubber gasket torn or is there a gap?" -> "Seals fine" (parsed `good`, meant `good`; H_L=0.8645, H_D=2.1814)
  - t=5 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=0.8645, H_D=1.9938)
- **c0001-codemixed_kn** (codemixed_kn): "fridge cooling agalla, suttalu jaaga ide, temperature knob kadime alli ide, there is no water anywhere"
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.6635, 6 turns, turn_budget)
  - normalised: "fridge cooling not happening, around space is there, temperature knob low in is there, there is no water anywhere"
  - interpretation p=0.5: `{"compartment_affected": "fridge", "placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_cold", "water_leak_location": "none"}`
  - interpretation p=0.125: `{"compartment_affected": "fridge", "placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm"}`
  - t=0 clarification `thermostat_setting`: "Just to check I understood: where is the temperature knob or setting - warm side, middle, or coldest?" -> "Warm side / lowest cooling" (parsed `too_warm`, meant `too_warm`; H_L=2.0, H_D=3.4689)
  - t=1 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "There is no fan inside" (parsed `not_applicable`, meant `not_applicable`; H_L=1.3961, H_D=2.9767)
  - t=2 clarification `placement_clearance`: "Just to check I understood: is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Plenty of space and shade" (parsed `adequate`, meant `adequate`; H_L=1.3628, H_D=2.5561)
  - t=3 clarification `water_leak_location`: "Just to check I understood: do you see water anywhere - inside at the bottom, or under the fridge?" -> "No water" (parsed `none`, meant `none`; H_L=1.3668, H_D=2.4368)
  - t=4 diagnostic `condenser_coils_dusty`: "Are the coils at the back or underneath covered in dust or lint?" -> "No, they look clean" (parsed `no`, meant `no`; H_L=1.4092, H_D=2.4351)
  - t=5 diagnostic `door_seal_condition`: "Does the door close and seal properly? Is the rubber gasket torn or is there a gap?" -> "Seals fine" (parsed `good`, meant `good`; H_L=1.3958, H_D=2.2599)
