# Railway cron service that starts the yt-checker check (see trigger.sh).
FROM alpine:3.22
RUN apk add --no-cache curl tzdata
COPY trigger.sh /trigger.sh
CMD ["sh", "/trigger.sh"]
