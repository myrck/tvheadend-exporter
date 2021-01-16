[![Contributors][contributors-shield]][contributors-url]


  <h3 align="center">TVHeadend Prometheus Exporter</h3>

### Running on Docker
```
docker run --network=host mcmarkj/tvheadend-exporter:latest
```

Metrics accessible at http://127.0.0.1:9249

Arguments are:
```
    --host  default=0.0.0.0 (bind host - 0.0.0.0 to allow outside connections)
    --port default='9429' (bind port i.e. what prometheus scrapes)
    --username (username for authentication, can be set via ENV Var TVH_USER')
    --password (password for authentication, can be set via ENV Var TVH_PASS)
    --server (server url for tvheadend, can be set via ENV Var TVH_SERVER)
```

<!-- Metrics Exporter -->

### Metrics

   ```sh
    # HELP tvheadend_subscription_count Number of active subscriptions
    # TYPE tvheadend_subscription_count gauge
    tvheadend_subscription_count 1.0

    # HELP tvheadend_active_subscription_start_time Start time for an active connection/stream to the TVHeadend Server
    # TYPE tvheadend_active_subscription_start_time gauge
    tvheadend_active_subscription_start_time 1.610810164e+09

    # HELP tvheadend_channel_count Number of channels on the server
    # TYPE tvheadend_channel_count gauge
    tvheadend_channel_count 153.0

    # HELP tvheadend_scrape_duration_seconds Duration of tvheadend scrape
    # TYPE tvheadend_scrape_duration_seconds gauge
    tvheadend_scrape_duration_seconds 0.05248594284057617
   ```



<!-- CONTRIBUTING -->
## Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/github_username/repo.svg?style=for-the-badge
[contributors-url]: https://github.com/mcmarkj/tvheadend-exporter/graphs/contributors
