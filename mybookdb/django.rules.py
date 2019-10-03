# adapted from sample in
# https://github.com/korfuri/django-prometheus/blob/master/examples/prometheus/django.rules

# Aggregate request counters
job:django_http_requests_before_middlewares_total:sum_rate30s = sum(rate(django_http_requests_before_middlewares_total[30s])) by (job)
job:django_http_requests_unknown_latency_total:sum_rate30s = sum(rate(django_http_requests_unknown_latency_total[30s])) by (job)
job:django_http_ajax_requests_total:sum_rate30s = sum(rate(django_http_ajax_requests_total[30s])) by (job)
job:django_http_responses_before_middlewares_total:sum_rate30s = sum(rate(django_http_responses_before_middlewares_total[30s])) by (job)
job:django_http_requests_unknown_latency_including_middlewares_total:sum_rate30s = sum(rate(django_http_requests_unknown_latency_including_middlewares_total[30s])) by (job)
job:django_http_requests_body_total_bytes:sum_rate30s = sum(rate(django_http_requests_body_total_bytes[30s])) by (job)
job:django_http_responses_streaming_total:sum_rate30s = sum(rate(django_http_responses_streaming_total[30s])) by (job)
job:django_http_responses_body_total_bytes:sum_rate30s = sum(rate(django_http_responses_body_total_bytes[30s])) by (job)
job:django_http_requests_total:sum_rate30s = sum(rate(django_http_requests_total_by_method[30s])) by (job)
job:django_http_requests_total_by_method:sum_rate30s = sum(rate(django_http_requests_total_by_method[30s])) by (job,method)
job:django_http_requests_total_by_transport:sum_rate30s = sum(rate(django_http_requests_total_by_transport[30s])) by (job,transport)
job:django_http_requests_total_by_view:sum_rate30s = sum(rate(django_http_requests_total_by_view_transport_method[30s])) by (job,view)
job:django_http_requests_total_by_view_transport_method:sum_rate30s = sum(rate(django_http_requests_total_by_view_transport_method[30s])) by (job,view,transport,method)
job:django_http_responses_total_by_templatename:sum_rate30s = sum(rate(django_http_responses_total_by_templatename[30s])) by (job,templatename)
job:django_http_responses_total_by_status:sum_rate30s = sum(rate(django_http_responses_total_by_status[30s])) by (job,status)
job:django_http_responses_total_by_status_name_method:sum_rate30s = sum(rate(django_http_responses_total_by_status_name_method[30s])) by (job,status,name,method)
job:django_http_responses_total_by_charset:sum_rate30s = sum(rate(django_http_responses_total_by_charset[30s])) by (job,charset)
job:django_http_exceptions_total_by_type:sum_rate30s = sum(rate(django_http_exceptions_total_by_type[30s])) by (job,type)
job:django_http_exceptions_total_by_view:sum_rate30s = sum(rate(django_http_exceptions_total_by_view[30s])) by (job,view)

# Aggregate latency histograms
job:django_http_requests_latency_including_middlewares_seconds:quantile_rate30s{quantile="50"} = histogram_quantile(0.50, sum(rate(django_http_requests_latency_including_middlewares_seconds_bucket[30s])) by (job, le))
job:django_http_requests_latency_including_middlewares_seconds:quantile_rate30s{quantile="95"} = histogram_quantile(0.95, sum(rate(django_http_requests_latency_including_middlewares_seconds_bucket[30s])) by (job, le))
job:django_http_requests_latency_including_middlewares_seconds:quantile_rate30s{quantile="99"} = histogram_quantile(0.99, sum(rate(django_http_requests_latency_including_middlewares_seconds_bucket[30s])) by (job, le))
job:django_http_requests_latency_including_middlewares_seconds:quantile_rate30s{quantile="99.9"} = histogram_quantile(0.999, sum(rate(django_http_requests_latency_including_middlewares_seconds_bucket[30s])) by (job, le))
job:django_http_requests_latency_seconds:quantile_rate30s{quantile="50"} = histogram_quantile(0.50, sum(rate(django_http_requests_latency_seconds_bucket[30s])) by (job, le))
job:django_http_requests_latency_seconds:quantile_rate30s{quantile="95"} = histogram_quantile(0.95, sum(rate(django_http_requests_latency_seconds_bucket[30s])) by (job, le))
job:django_http_requests_latency_seconds:quantile_rate30s{quantile="99"} = histogram_quantile(0.99, sum(rate(django_http_requests_latency_seconds_bucket[30s])) by (job, le))
job:django_http_requests_latency_seconds:quantile_rate30s{quantile="99.9"} = histogram_quantile(0.999, sum(rate(django_http_requests_latency_seconds_bucket[30s])) by (job, le))

# Aggregate model operations
job:django_model_inserts_total:sum_rate1m = sum(rate(django_model_inserts_total[1m])) by (job, model)
job:django_model_updates_total:sum_rate1m = sum(rate(django_model_updates_total[1m])) by (job, model)
job:django_model_deletes_total:sum_rate1m = sum(rate(django_model_deletes_total[1m])) by (job, model)

# Aggregate database operations
job:django_db_new_connections_total:sum_rate30s = sum(rate(django_db_new_connections_total[30s])) by (alias, vendor)
job:django_db_new_connection_errors_total:sum_rate30s = sum(rate(django_db_new_connection_errors_total[30s])) by (alias, vendor)
job:django_db_execute_total:sum_rate30s = sum(rate(django_db_execute_total[30s])) by (alias, vendor)
job:django_db_execute_many_total:sum_rate30s = sum(rate(django_db_execute_many_total[30s])) by (alias, vendor)
job:django_db_errors_total:sum_rate30s = sum(rate(django_db_errors_total[30s])) by (alias, vendor, type)

# Aggregate migrations
job:django_migrations_applied_total:max = max(django_migrations_applied_total) by (job, connection)
job:django_migrations_unapplied_total:max = max(django_migrations_unapplied_total) by (job, connection)



# Alerts
ALERT UnappliedMigrations
  IF job:django_migrations_unapplied_total:max > 0
  FOR 1m
  WITH {
    severity="testing"
  }
  SUMMARY "Unapplied django migrations on {{$labels.connection}}"
  DESCRIPTION "Django detected {{$value}} unapplied migrations on database {{$labels.connection}}"


