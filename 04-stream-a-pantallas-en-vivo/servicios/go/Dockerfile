# Una sola imagen con las tres piezas en Go: generador, sonda y consumidor.
FROM golang:1.27-alpine AS compilar
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /salida/ ./cmd/...

FROM alpine:3.22
COPY --from=compilar /salida/ /usr/local/bin/
