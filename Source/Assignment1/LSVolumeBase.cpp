// See LSVolumeBase.h for this class's purpose, pattern and connections.

#include "LSVolumeBase.h"

#include "Components/BoxComponent.h"

ALSVolumeBase::ALSVolumeBase()
{
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	SetRootComponent(Box);
	Box->SetBoxExtent(FVector(200.f));
	Box->SetCollisionProfileName(TEXT("Trigger"));
}
