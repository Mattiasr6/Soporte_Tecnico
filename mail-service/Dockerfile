FROM php:8.2-cli

RUN apt-get update && apt-get install -y git unzip && \
    curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

WORKDIR /app
COPY composer.json .
RUN composer install --no-interaction --no-dev --optimize-autoloader

COPY send.php .

EXPOSE 8080

CMD ["php", "-S", "0.0.0.0:8080", "send.php"]
