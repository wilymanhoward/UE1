// See LSLavaSplash.h for this class's purpose and connections.

#include "LSLavaSplash.h"

#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "LSDefaultMeshes.h"

namespace
{
	constexpr int32 DropletCount = 28;
	constexpr float Gravity = 980.f;
}

ALSLavaSplash::ALSLavaSplash()
{
	PrimaryActorTick.bCanEverTick = true;

	Flash = CreateDefaultSubobject<UPointLightComponent>(TEXT("Flash"));
	SetRootComponent(Flash);
	Flash->SetLightColor(FLinearColor(1.f, 0.35f, 0.08f));
	Flash->SetAttenuationRadius(900.f);
	Flash->SetCastShadows(false);
	Flash->SetIntensity(0.f);

	DropletMesh = LSDefaultMeshes::Sphere();
}

void ALSLavaSplash::Burst(UMaterialInterface* DropletMaterial, float Size)
{
	Size = FMath::Max(Size, 0.1f);
	FlashIntensity = 60000.f * Size;
	Flash->SetIntensity(FlashIntensity);
	SetLifeSpan(Lifetime + 0.1f);

	for (int32 Index = 0; Index < DropletCount; ++Index)
	{
		// A third shoot nearly straight up as the splash's column, the rest fan out as its crown.
		const bool bColumn = Index % 3 == 0;
		const float Tilt = FMath::DegreesToRadians(bColumn ? FMath::FRandRange(0.f, 15.f) : FMath::FRandRange(30.f, 60.f));
		const float Turn = FMath::FRandRange(0.f, 2.f * PI);
		const FVector Direction(FMath::Sin(Tilt) * FMath::Cos(Turn), FMath::Sin(Tilt) * FMath::Sin(Turn), FMath::Cos(Tilt));
		const float Speed = (bColumn ? FMath::FRandRange(650.f, 900.f) : FMath::FRandRange(380.f, 620.f)) * FMath::Sqrt(Size);

		UStaticMeshComponent* Droplet = NewObject<UStaticMeshComponent>(this);
		Droplet->SetStaticMesh(DropletMesh);
		Droplet->SetMaterial(0, DropletMaterial);
		Droplet->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Droplet->SetCastShadow(false);
		Droplet->SetupAttachment(Flash);
		Droplet->SetUsingAbsoluteLocation(true);
		Droplet->SetWorldLocation(GetActorLocation() + Direction * 20.f * Size);
		const float Scale = FMath::FRandRange(0.12f, 0.3f) * Size;
		Droplet->SetWorldScale3D(FVector(Scale));
		Droplet->RegisterComponent();

		Droplets.Add(Droplet);
		Velocities.Add(Direction * Speed);
		BaseScales.Add(Scale);
	}
}

void ALSLavaSplash::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	Age += DeltaSeconds;
	const float Left = FMath::Clamp(1.f - Age / Lifetime, 0.f, 1.f);
	Flash->SetIntensity(FlashIntensity * Left * Left);

	const float SurfaceZ = GetActorLocation().Z;
	for (int32 Index = 0; Index < Droplets.Num(); ++Index)
	{
		UStaticMeshComponent* Droplet = Droplets[Index];
		if (!Droplet->IsVisible())
		{
			continue;
		}
		Velocities[Index].Z -= Gravity * DeltaSeconds;
		const FVector Location = Droplet->GetComponentLocation() + Velocities[Index] * DeltaSeconds;
		Droplet->SetWorldLocation(Location);
		// Stretched along its flight, so a fast blob reads as a flung drop rather than a ball.
		const float Stretch = 1.f + FMath::Min(Velocities[Index].Size() / 900.f, 1.2f);
		Droplet->SetWorldRotation(Velocities[Index].Rotation() + FRotator(-90.f, 0.f, 0.f));
		Droplet->SetWorldScale3D(FVector(1.f, 1.f, Stretch) * BaseScales[Index] * FMath::Sqrt(Left));
		// Back into the lava it came from.
		if (Location.Z < SurfaceZ - 10.f && Velocities[Index].Z < 0.f)
		{
			Droplet->SetVisibility(false);
		}
	}
}
