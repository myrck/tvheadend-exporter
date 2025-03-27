[![Contributors][contributors-shield]][contributors-url]
[![Contributors][docker-build-shield]][build-url]

  <h3 align="center">TVHeadend Prometheus Exporter</h3>

### Running on Docker
```
docker run --network=host ghcr.io/0x4d4d/tvheadend-exporter:latest
```

Metrics accessible at http://127.0.0.1:9429

Arguments are:
```
    --host  default=0.0.0.0 (bind host - 0.0.0.0 to allow outside connections)
    --port default='9429' (bind port i.e. what prometheus scrapes)
    --username (username for authentication, can be set via ENV Var TVH_USER)
    --password (password for authentication, can be set via ENV Var TVH_PASS)
    --server (server IP for tvheadend, can be set via ENV Var TVH_SERVER)
    --serverport (server port for tvheadend, can be set via ENV Var TVH_PORT)
```

<!-- Metrics Exporter -->

### Metrics

   ```sh
# HELP tvheadend_subscription_count Number of active subscriptions
# TYPE tvheadend_subscription_count gauge
tvheadend_subscription_count 1.0

# HELP tvheadend_input_signal Signal Strength for DVB Inputs
# TYPE tvheadend_input_signal gauge
tvheadend_input_signal{name="Sony CXD2880 #0 : DVB-T #0",stream="746MHz in DVB-T Network"} 1.8446744073709492e+19

# HELP tvheadend_scrape_duration_seconds Duration of TVHeadend scrape
# TYPE tvheadend_scrape_duration_seconds gauge
tvheadend_scrape_duration_seconds 0.10399699211120605

# HELP tvheadend_input_signal_noise_ratio_scale A value of 1 indicates that the corresponding signal or SNR readingis relative
# TYPE tvheadend_input_signal_noise_ratio_scale gauge
tvheadend_input_signal_noise_ratio_scale{name="Sony CXD2880 #0 : DVB-T #0",stream="746MHz in DVB-T Network"} 2.0

# HELP tvheadend_dvr_start_time Start time for DVR Event
# TYPE tvheadend_dvr_start_time gauge
tvheadend_dvr_start_time{channel_name="Channel 4 HD",programme_title="Back",state="scheduled",status="Scheduled for recording"} 1.6112664e+09
tvheadend_dvr_start_time{channel_name="Channel 4 HD",programme_title="New: Gogglebox",state="completedError",status="File missing"} 1.6022736e+09

# HELP tvheadend_dvr_start_time Duration for DVR Event
# TYPE tvheadend_dvr_start_time gauge
tvheadend_dvr_start_time{channel_name="Channel 4 HD",programme_title="Back",state="scheduled",status="Scheduled for recording"} 2220.0
tvheadend_dvr_start_time{channel_name="Channel 4 HD",programme_title="New: Gogglebox",state="completedError",status="File missing"} 3720.0

# HELP tvheadend_channel_count Number of channels on the server
# TYPE tvheadend_channel_count gauge
tvheadend_channel_count 145.0

# HELP tvheadend_input_continuity_errors Continuity Errors for Inputs
# TYPE tvheadend_input_continuity_errors gauge
tvheadend_input_continuity_errors{name="Sony CXD2880 #0 : DVB-T #0",stream="746MHz in DVB-T Network"} 0.0

# HELP tvheadend_dvr_count Number of events in the DVR
# TYPE tvheadend_dvr_count gauge
tvheadend_dvr_count{status="upcoming"} 1.0
tvheadend_dvr_count{status="finished"} 0.0
tvheadend_dvr_count{status="failed"} 0.0

# HELP tvheadend_input_signal_noise_ratio Signal Noise Ratio for DVB Inputs
# TYPE tvheadend_input_signal_noise_ratio gauge
tvheadend_input_signal_noise_ratio{name="Sony CXD2880 #0 : DVB-T #0",stream="746MHz in DVB-T Network"} 27353.0

# HELP tvheadend_dvr_start_time Finish time for DVR Event
# TYPE tvheadend_dvr_start_time gauge
tvheadend_dvr_start_time{channel_name="Channel 4 HD",programme_title="Back",state="scheduled",status="Scheduled for recording"} 1.6112685e+09
tvheadend_dvr_start_time{channel_name="Channel 4 HD",programme_title="New: Gogglebox",state="completedError",status="File missing"} 1.6022772e+09

# HELP tvheadend_active_subscription_start_time Start time for an active connection to the TVHeadend Server
# TYPE tvheadend_active_subscription_start_time gauge
tvheadend_active_subscription_start_time 1.610886044e+09

# HELP tvheadend_input_signal_scale A value of 1 indicates that the corresponding signal or SNR reading is relative
# TYPE tvheadend_input_signal_scale gauge
tvheadend_input_signal_scale{name="Sony CXD2880 #0 : DVB-T #0",stream="746MHz in DVB-T Network"} 2.0

# HELP tvheadend_epg_count Number of programmes in the EPG
# TYPE tvheadend_epg_count gauge
tvheadend_epg_count 25308.0
   ```

*For signal_scale and snr_scale, a value of 1 indicates that the corresponding signal or SNR reading is relative; 65535 = 100%. A value of 2 indicates the reading is absolute; 1000 = 1dB. A value of 0 indicates that the reading is not available or not valid.*


<!-- CONTRIBUTING -->
## Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/mcmarkj/tvheadend-exporter.svg?style=for-the-badge
[contributors-url]: https://github.com/mcmarkj/tvheadend-exporter/graphs/contributors
[build-url]: https://github.com/mcmarkj/tvheadend-exporter/actions?query=workflow%3Aci
[docker-build-shield]: https://img.shields.io/github/workflow/status/mcmarkj/tvheadend-exporter/ci?label=CI%20CD&style=for-the-badge
