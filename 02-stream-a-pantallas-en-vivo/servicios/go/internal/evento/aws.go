package evento

import (
	"context"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
)

// ConfigAWS arma la configuración para hablar con un emulador local: región fija y credenciales
// de mentira, que el emulador no revisa. Contra AWS real, este bloque se reemplaza por
// config.LoadDefaultConfig(ctx) y el SDK toma el rol de la máquina.
func ConfigAWS(ctx context.Context) (aws.Config, error) {
	return config.LoadDefaultConfig(ctx, config.WithRegion("us-east-1"),
		config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider("local", "local", "")))
}
