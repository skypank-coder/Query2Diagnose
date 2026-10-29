# Error analysis: `q2d` in run `20261029T071216Z-pilot`

49 of 105 dialogues end with the wrong action. Buckets are checked in the order below; each failure counts once.

| Cause | Failures | Share |
|---|---|---|
| misparsed_negation | 0 | 0% |
| missed_codemixed_token | 7 | 14% |
| wrong_clarification | 13 | 27% |
| retrieval_miss | 3 | 6% |
| premature_stop | 5 | 10% |
| hypothesis_model_gap | 21 | 43% |

## missed_codemixed_token

- **c0001-codemixed_hi** (codemixed_hi): "fridge bilkul thanda nahi kar raha, aas paas kaafi jagah hai, the dial is turned to the lowest cooling, kahin paani nahi hai"
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.6558, 6 turns, turn_budget)
  - normalised: "fridge completely cold not doing, aas near kaafi space is, the dial is turned to the lowest cooling, anywhere water not is"
  - interpretation p=0.25: `{"compartment_affected": "fridge", "primary_symptom": "not_cooling", "thermostat_setting": "too_cold"}`
  - interpretation p=0.25: `{"compartment_affected": "fridge", "power_supply_ok": "yes", "primary_symptom": "not_cooling"}`
  - t=0 clarification `thermostat_setting`: "Just to check I understood: where is the temperature knob or setting - warm side, middle, or coldest?" -> "Warm side / lowest cooling" (parsed `too_warm`, meant `too_warm`; H_L=2.0, H_D=3.5119)
  - t=1 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=1.0109, H_D=2.92)
  - t=2 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=0.9973, H_D=2.65)
  - t=3 clarification `placement_clearance`: "Just to check I understood: is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Plenty of space and shade" (parsed `adequate`, meant `adequate`; H_L=0.9843, H_D=2.3704)
  - t=4 diagnostic `power_supply_ok`: "When you open the door, does the light inside come on (or the display light up)?" -> "Yes, the light comes on" (parsed `yes`, meant `yes`; H_L=0.8705, H_D=2.277)
  - t=5 diagnostic `recent_relocation`: "Was the fridge moved or newly installed in the last few days?" -> "No" (parsed `no`, meant `no`; H_L=0.9356, H_D=2.1583)
- **c0001-codemixed_kn** (codemixed_kn): "fridge cooling agalla, suttalu jaaga ide, temperature knob kadime alli ide, there is no water anywhere"
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.3662, 6 turns, turn_budget)
  - normalised: "fridge cooling not happening, around space is there, temperature knob low in is there, there is no water anywhere"
  - interpretation p=0.25: `{"compartment_affected": "fridge", "primary_symptom": "not_cooling", "thermostat_setting": "too_cold"}`
  - interpretation p=0.25: `{"compartment_affected": "fridge", "placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_cold"}`
  - t=0 clarification `placement_clearance`: "Just to check I understood: is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Plenty of space and shade" (parsed `adequate`, meant `adequate`; H_L=2.0, H_D=3.6368)
  - t=1 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=1.9821, H_D=3.5506)
  - t=2 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=1.9824, H_D=3.42)
  - t=3 clarification `water_leak_location`: "Just to check I understood: do you see water anywhere - inside at the bottom, or under the fridge?" -> "No water" (parsed `none`, meant `none`; H_L=1.9826, H_D=3.2551)
  - t=4 diagnostic `power_supply_ok`: "When you open the door, does the light inside come on (or the display light up)?" -> "Yes, the light comes on" (parsed `yes`, meant `yes`; H_L=1.9539, H_D=3.2368)
  - t=5 diagnostic `condenser_coils_dusty`: "Are the coils at the back or underneath covered in dust or lint?" -> "No, they look clean" (parsed `no`, meant `no`; H_L=1.954, H_D=3.119)
- **c0001-combined_hi** (combined_hi): "fridge cooling nahi ho rahi, aas paas kaafi jagah ha, kahin paani nahi hai"
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.6236, 6 turns, turn_budget)
  - normalised: "fridge cooling not is happening, aas near kaafi space ha, anywhere water not is"
  - interpretation p=0.5: `{"compartment_affected": "fridge", "placement_clearance": "adequate", "primary_symptom": "not_cooling"}`
  - interpretation p=0.25: `{"compartment_affected": "fridge", "placement_clearance": "adequate", "primary_symptom": "not_cooling", "water_leak_location": "none"}`
  - t=0 diagnostic `thermostat_setting`: "Where is the temperature knob or setting - warm side, middle, or coldest?" -> "Warm side / lowest cooling" (parsed `too_warm`, meant `too_warm`; H_L=1.5, H_D=3.649)
  - t=1 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=1.4954, H_D=2.9672)
  - t=2 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=1.4968, H_D=2.7027)
  - t=3 clarification `placement_clearance`: "Just to check I understood: is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Plenty of space and shade" (parsed `adequate`, meant `adequate`; H_L=1.498, H_D=2.427)
  - t=4 clarification `water_leak_location`: "Just to check I understood: do you see water anywhere - inside at the bottom, or under the fridge?" -> "No water" (parsed `none`, meant `none`; H_L=1.451, H_D=2.3378)
  - t=5 diagnostic `power_supply_ok`: "When you open the door, does the light inside come on (or the display light up)?" -> "Yes, the light comes on" (parsed `yes`, meant `yes`; H_L=1.4777, H_D=2.3114)

## wrong_clarification

- **c0001-spelling** (spelling): "It has stopped cooling priperly. There is no water anywherd, thee temperature knob is on the waarmest stting and it has plenty of space aorund it."
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.5947, 6 turns, turn_budget)
  - normalised: "It has stopped cooling properly. There is no water anywhere, fine temperature knob is on the warmest setting and it has plenty of space around it."
  - interpretation p=0.75: `{"placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm"}`
  - interpretation p=0.25: `{"compartment_affected": "both", "placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm"}`
  - t=0 clarification `compartment_affected`: "Just to check I understood: which part has the problem - the fridge section, the freezer, or both?" -> "Fridge section" (parsed `not_sure`, meant `fridge`; H_L=0.8113, H_D=3.3657)
  - t=1 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=0.8113, H_D=3.3657)
  - t=2 diagnostic `power_supply_ok`: "When you open the door, does the light inside come on (or the display light up)?" -> "Yes, the light comes on" (parsed `yes`, meant `yes`; H_L=0.8269, H_D=3.1363)
  - t=3 diagnostic `recent_relocation`: "Was the fridge moved or newly installed in the last few days?" -> "No" (parsed `no`, meant `no`; H_L=0.803, H_D=3.0091)
  - t=4 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=0.7726, H_D=2.8516)
  - t=5 diagnostic `compressor_running`: "Is the compressor (the motor at the lower back) running? You can usually hear a hum or feel it vibrate." -> "Yes, it is running" (parsed `yes`, meant `yes`; H_L=0.749, H_D=2.591)
- **c0029-clean** (clean): "My fridge is not cooling. The motor at the back is humming."
  - gold fault `door_seal`, gold action `door_seal`; predicted `REFER` (top `defrost_system_failure`, p=0.2644, 6 turns, turn_budget)
  - normalised: "My fridge is not cooling. The motor at the back is humming."
  - interpretation p=0.75: `{"compartment_affected": "fridge", "compressor_running": "yes", "noise_location": "back_bottom", "noise_type": "normal_hum", "primary_symptom": "not_cooling"}`
  - interpretation p=0.25: `{"compartment_affected": "fridge", "compressor_running": "yes", "primary_symptom": "not_cooling"}`
  - t=0 clarification `noise_location`: "Just to check I understood: where does the unusual sound come from - inside the fridge or freezer, or the lower back of the unit?" -> "There is no unusual sound" (parsed `not_sure`, meant `not_applicable`; H_L=0.8113, H_D=3.5021)
  - t=1 clarification `noise_type`: "Just to check I understood: what kind of sound does it make?" -> "Just the usual soft hum" (parsed `normal_hum`, meant `normal_hum`; H_L=0.8113, H_D=3.5021)
  - t=2 diagnostic `thermostat_setting`: "Where is the temperature knob or setting - warm side, middle, or coldest?" -> "Middle / normal" (parsed `normal`, meant `normal`; H_L=0.5032, H_D=3.4709)
  - t=3 diagnostic `placement_clearance`: "Is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Plenty of space and shade" (parsed `adequate`, meant `adequate`; H_L=0.4962, H_D=3.4687)
  - t=4 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Frost-free" (parsed `frost_free`, meant `frost_free`; H_L=0.4887, H_D=3.4532)
  - t=5 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "Yes, the fan runs" (parsed `yes`, meant `yes`; H_L=0.4816, H_D=3.2172)
- **c0061-codemixed_hi** (codemixed_hi): "fridge cooling nahi ho rahi, it only makes the usual soft hum, temperature setting normal hai"
  - gold fault `hot_surroundings`, gold action `hot_surroundings`; predicted `REFER` (top `hot_surroundings`, p=0.6282, 6 turns, turn_budget)
  - normalised: "fridge cooling not is happening, it only makes the usual soft hum, temperature setting normal is"
  - interpretation p=0.25: `{"compartment_affected": "fridge", "noise_location": "back_bottom", "noise_type": "normal_hum", "primary_symptom": "not_cooling", "thermostat_setting": "normal"}`
  - interpretation p=0.25: `{"compartment_affected": "fridge", "noise_location": "back_bottom", "noise_type": "normal_hum", "primary_symptom": "not_cooling"}`
  - t=0 clarification `noise_location`: "Just to check I understood: where does the unusual sound come from - inside the fridge or freezer, or the lower back of the unit?" -> "There is no unusual sound" (parsed `not_sure`, meant `not_applicable`; H_L=2.0, H_D=3.6153)
  - t=1 clarification `thermostat_setting`: "Just to check I understood: where is the temperature knob or setting - warm side, middle, or coldest?" -> "Middle / normal" (parsed `normal`, meant `normal`; H_L=2.0, H_D=3.6153)
  - t=2 diagnostic `placement_clearance`: "Is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Near heat or no space" (parsed `too_close_or_hot`, meant `too_close_or_hot`; H_L=1.9421, H_D=3.5204)
  - t=3 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=1.9362, H_D=2.8818)
  - t=4 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=1.9379, H_D=2.5792)
  - t=5 clarification `compressor_running`: "Just to check I understood: is the compressor (the motor at the lower back) running? You can usually hear a hum or feel it vibrate." -> "Yes, it is running" (parsed `yes`, meant `yes`; H_L=1.9375, H_D=2.2871)

## retrieval_miss

- **c0210-combined_hi** (combined_hi): "fridge bilkuul band pada hai"
  - gold fault `power_supply`, gold action `power_supply`; predicted `REFER` (top `power_supply`, p=0.8933, 6 turns, unsupported)
  - normalised: "fridge completely off lying is"
  - interpretation p=0.5: `{"compartment_affected": "fridge", "primary_symptom": "not_powering_on"}`
  - interpretation p=0.25: `{"compartment_affected": "fridge", "primary_symptom": "not_cooling"}`
  - t=0 clarification `primary_symptom`: "Just to check I understood: what is the main problem with the fridge?" -> "Will not turn on" (parsed `not_powering_on`, meant `not_powering_on`; H_L=1.5, H_D=3.0918)
  - t=1 clarification `power_supply_ok`: "Just to check I understood: when you open the door, does the light inside come on (or the display light up)?" -> "No light at all" (parsed `no`, meant `no`; H_L=0.9412, H_D=2.5862)
  - t=2 diagnostic `compressor_running`: "Is the compressor (the motor at the lower back) running? You can usually hear a hum or feel it vibrate." -> "No, it is silent" (parsed `no`, meant `no`; H_L=1.0097, H_D=1.9139)
  - t=3 diagnostic `recent_relocation`: "Was the fridge moved or newly installed in the last few days?" -> "No" (parsed `no`, meant `no`; H_L=1.0048, H_D=1.2884)
  - t=4 diagnostic `noise_type`: "What kind of sound does it make?" -> "No sound at all" (parsed `none`, meant `none`; H_L=1.0046, H_D=1.2124)
  - t=5 diagnostic `works_in_other_socket`: "If you plug the fridge into a different socket (or use an extension to another one), does it turn on?" -> "Yes, it works there" (parsed `yes`, meant `yes`; H_L=1.0017, H_D=0.7738)
- **c0210-combined_kn** (combined_kn): "fidge full dead aaggide"
  - gold fault `power_supply`, gold action `power_supply`; predicted `REFER` (top `power_supply`, p=0.9263, 6 turns, unsupported)
  - normalised: "fridge full dead has become"
  - interpretation p=0.25: `{"compartment_affected": "fridge", "primary_symptom": "not_powering_on", "vents_blocked_or_overloaded": "yes"}`
  - interpretation p=0.25: `{"compartment_affected": "fridge", "primary_symptom": "not_cooling"}`
  - t=0 clarification `primary_symptom`: "Just to check I understood: what is the main problem with the fridge?" -> "Will not turn on" (parsed `not_powering_on`, meant `not_powering_on`; H_L=2.0, H_D=3.7325)
  - t=1 diagnostic `power_supply_ok`: "When you open the door, does the light inside come on (or the display light up)?" -> "No light at all" (parsed `no`, meant `no`; H_L=0.1878, H_D=2.9737)
  - t=2 diagnostic `compressor_running`: "Is the compressor (the motor at the lower back) running? You can usually hear a hum or feel it vibrate." -> "No, it is silent" (parsed `no`, meant `no`; H_L=0.1308, H_D=2.1607)
  - t=3 diagnostic `noise_type`: "What kind of sound does it make?" -> "No sound at all" (parsed `none`, meant `none`; H_L=0.0914, H_D=1.4618)
  - t=4 diagnostic `evaporator_fan_running`: "Open the freezer and press the door switch - can you hear or feel the fan inside running?" -> "No, it does not run" (parsed `no`, meant `no`; H_L=0.0656, H_D=0.8934)
  - t=5 diagnostic `works_in_other_socket`: "If you plug the fridge into a different socket (or use an extension to another one), does it turn on?" -> "Yes, it works there" (parsed `yes`, meant `yes`; H_L=0.0543, H_D=0.5672)
- **c0210-incomplete** (incomplete): "My fridge is completely dead."
  - gold fault `power_supply`, gold action `power_supply`; predicted `REFER` (top `power_supply`, p=0.9404, 5 turns, unsupported)
  - normalised: "My fridge is completely dead."
  - interpretation p=0.25: `{"compartment_affected": "fridge", "compressor_running": "no", "power_supply_ok": "no", "primary_symptom": "not_powering_on"}`
  - interpretation p=0.25: `{"compartment_affected": "both", "primary_symptom": "not_powering_on"}`
  - t=0 clarification `compartment_affected`: "Just to check I understood: which part has the problem - the fridge section, the freezer, or both?" -> "Both" (parsed `both`, meant `both`; H_L=2.0, H_D=2.1367)
  - t=1 diagnostic `power_supply_ok`: "When you open the door, does the light inside come on (or the display light up)?" -> "No light at all" (parsed `no`, meant `no`; H_L=0.4936, H_D=2.1814)
  - t=2 diagnostic `recent_relocation`: "Was the fridge moved or newly installed in the last few days?" -> "No" (parsed `no`, meant `no`; H_L=0.5632, H_D=1.1201)
  - t=3 diagnostic `compressor_running`: "Is the compressor (the motor at the lower back) running? You can usually hear a hum or feel it vibrate." -> "No, it is silent" (parsed `no`, meant `no`; H_L=0.5678, H_D=0.9841)
  - t=4 diagnostic `noise_type`: "What kind of sound does it make?" -> "No sound at all" (parsed `none`, meant `none`; H_L=0.5848, H_D=0.6651)

## premature_stop

- **c0166-clean** (clean): "The walls are covered in frost in the freezer. It is not overloaded, there is frost on the back wall inside and it has plenty of space around it."
  - gold fault `excess_frost_manual_defrost`, gold action `REFER`; predicted `excess_frost_manual_defrost` (top `excess_frost_manual_defrost`, p=0.8064, 1 turns, confident_and_supported)
  - normalised: "The walls are covered in frost in the freezer. It is not overloaded, there is frost on the back wall inside and it has plenty of space around it."
  - interpretation p=0.75: `{"compartment_affected": "freezer", "frost_on_back_wall": "yes", "placement_clearance": "adequate", "primary_symptom": "frost_buildup", "vents_blocked_or_overloaded": "no"}`
  - interpretation p=0.25: `{"compartment_affected": "freezer", "frost_on_back_wall": "yes", "placement_clearance": "adequate", "primary_symptom": "frost_buildup"}`
  - t=0 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=0.8113, H_D=1.8966)
- **c0166-codemixed_hi** (codemixed_hi): "freezer mein deewaron pe bahut frost jam raha hai, it is not overloaded, aas paas kaafi jagah hai, peeche ki deewar pe barf jami hai"
  - gold fault `excess_frost_manual_defrost`, gold action `REFER`; predicted `excess_frost_manual_defrost` (top `excess_frost_manual_defrost`, p=0.7526, 1 turns, confident_and_supported)
  - normalised: "freezer in walls on very frost jam kept is, it is not overloaded, aas near kaafi space is, behind ki wall on ice frozen is"
  - interpretation p=0.5: `{"compartment_affected": "freezer", "frost_on_back_wall": "yes", "placement_clearance": "adequate", "primary_symptom": "frost_buildup", "vents_blocked_or_overloaded": "no"}`
  - interpretation p=0.25: `{"compartment_affected": "freezer", "frost_on_back_wall": "yes", "primary_symptom": "frost_buildup"}`
  - t=0 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=1.5, H_D=2.11)
- **c0166-combined_kn** (combined_kn): "freezer alli frost jaasti aagide, it is not overloaded"
  - gold fault `excess_frost_manual_defrost`, gold action `REFER`; predicted `excess_frost_manual_defrost` (top `excess_frost_manual_defrost`, p=0.7944, 2 turns, confident_and_supported)
  - normalised: "freezer in frost too much has become, it is not overloaded"
  - interpretation p=0.75: `{"compartment_affected": "freezer", "primary_symptom": "frost_buildup", "vents_blocked_or_overloaded": "no"}`
  - interpretation p=0.25: `{"compartment_affected": "freezer", "primary_symptom": "frost_buildup"}`
  - t=0 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=0.8113, H_D=2.5289)
  - t=1 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "Yes, there is frost" (parsed `yes`, meant `yes`; H_L=0.8058, H_D=1.8088)

## hypothesis_model_gap

- **c0001-clean** (clean): "It has stopped cooling properly. There is no water anywhere, the temperature knob is on the warmest setting and it has plenty of space around it."
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.6704, 6 turns, turn_budget)
  - normalised: "It has stopped cooling properly. There is no water anywhere, the temperature knob is on the warmest setting and it has plenty of space around it."
  - interpretation p=0.75: `{"placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm", "water_leak_location": "none"}`
  - interpretation p=0.25: `{"placement_clearance": "adequate", "primary_symptom": "not_cooling", "thermostat_setting": "too_warm"}`
  - t=0 diagnostic `compartment_affected`: "Which part has the problem - the fridge section, the freezer, or both?" -> "Fridge section" (parsed `fridge`, meant `fridge`; H_L=0.8113, H_D=3.1963)
  - t=1 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=0.8112, H_D=2.824)
  - t=2 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=0.8115, H_D=2.5401)
  - t=3 clarification `water_leak_location`: "Just to check I understood: do you see water anywhere - inside at the bottom, or under the fridge?" -> "No water" (parsed `none`, meant `none`; H_L=0.8117, H_D=2.2452)
  - t=4 diagnostic `power_supply_ok`: "When you open the door, does the light inside come on (or the display light up)?" -> "Yes, the light comes on" (parsed `yes`, meant `yes`; H_L=0.6857, H_D=2.2361)
  - t=5 diagnostic `recent_relocation`: "Was the fridge moved or newly installed in the last few days?" -> "No" (parsed `no`, meant `no`; H_L=0.6857, H_D=2.0935)
- **c0001-combined_kn** (combined_kn): "fridge tannage aagta illa, there is no water anywhere"
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.62, 6 turns, turn_budget)
  - normalised: "fridge cold not happening, there is no water anywhere"
  - interpretation p=0.75: `{"compartment_affected": "fridge", "primary_symptom": "not_cooling", "water_leak_location": "none"}`
  - interpretation p=0.25: `{"compartment_affected": "fridge", "primary_symptom": "not_cooling"}`
  - t=0 diagnostic `thermostat_setting`: "Where is the temperature knob or setting - warm side, middle, or coldest?" -> "Warm side / lowest cooling" (parsed `too_warm`, meant `too_warm`; H_L=0.8113, H_D=3.6582)
  - t=1 diagnostic `placement_clearance`: "Is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Plenty of space and shade" (parsed `adequate`, meant `adequate`; H_L=0.8104, H_D=3.0426)
  - t=2 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=0.8105, H_D=2.9103)
  - t=3 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=0.8108, H_D=2.636)
  - t=4 clarification `water_leak_location`: "Just to check I understood: do you see water anywhere - inside at the bottom, or under the fridge?" -> "No water" (parsed `none`, meant `none`; H_L=0.8111, H_D=2.3497)
  - t=5 diagnostic `power_supply_ok`: "When you open the door, does the light inside come on (or the display light up)?" -> "Yes, the light comes on" (parsed `yes`, meant `yes`; H_L=0.6848, H_D=2.3404)
- **c0001-incomplete** (incomplete): "The cooling is very weak. There is no water anywhere."
  - gold fault `thermostat_setting`, gold action `thermostat_setting`; predicted `REFER` (top `thermostat_setting`, p=0.585, 6 turns, turn_budget)
  - normalised: "The cooling is very weak. There is no water anywhere."
  - interpretation p=0.5: `{"primary_symptom": "not_cooling", "water_leak_location": "none"}`
  - interpretation p=0.5: `{"primary_symptom": "not_cooling"}`
  - t=0 diagnostic `placement_clearance`: "Is the fridge close to a stove or in direct sun, or pushed tight against the wall?" -> "Plenty of space and shade" (parsed `adequate`, meant `adequate`; H_L=1.0, H_D=3.8157)
  - t=1 diagnostic `cooling_type`: "Is it a frost-free fridge, or a direct-cool one that you defrost by hand?" -> "Direct-cool (manual defrost)" (parsed `direct_cool`, meant `direct_cool`; H_L=1.0, H_D=3.7616)
  - t=2 diagnostic `frost_on_back_wall`: "Is there frost or ice on the back wall inside the freezer or fridge?" -> "No frost" (parsed `no`, meant `no`; H_L=1.0, H_D=3.5246)
  - t=3 diagnostic `thermostat_setting`: "Where is the temperature knob or setting - warm side, middle, or coldest?" -> "Warm side / lowest cooling" (parsed `too_warm`, meant `too_warm`; H_L=1.0, H_D=3.4607)
  - t=4 diagnostic `compartment_affected`: "Which part has the problem - the fridge section, the freezer, or both?" -> "Fridge section" (parsed `fridge`, meant `fridge`; H_L=1.0, H_D=2.8282)
  - t=5 clarification `water_leak_location`: "Just to check I understood: do you see water anywhere - inside at the bottom, or under the fridge?" -> "No water" (parsed `none`, meant `none`; H_L=1.0, H_D=2.4009)
