// See SinkingPad.h for this class's purpose and connections.

#include "SinkingPad.h"

#include "Components/StaticMeshComponent.h"

ASinkingPad::ASinkingPad()
{
	ShakeDuration = 0.3f;
	ShakeAmplitude = 1.f;
	FallSpeed = 50.f;
	FallDistance = 160.f;
	RespawnDelay = 2.f;
	bVanishAfterFall = false;
	ReturnSpeed = 80.f;

	Mesh->SetRelativeScale3D(FVector(2.5f, 2.5f, 0.2f));
}
