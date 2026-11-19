// See FormFlower.h for this class's purpose, pattern and connections.

#include "FormFlower.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "LSGameInstance.h"
#include "LSPlayerController.h"
#include "SeedBall.h"

void AFormFlower::OnCollected(ASeedBall* Ball)
{
	if (ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
	{
		GameInstance->UnlockForm(FormToUnlock);
		GameInstance->SaveProgress();
	}

	if (ALSPlayerController* PlayerController = Ball->GetController<ALSPlayerController>())
	{
		PlayerController->ShowFormUnlock(FormToUnlock, PromptMessage, PromptDuration);
	}

	if (CollectChipMesh)
	{
		for (int32 Index = 0; Index < 4; ++Index)
		{
			const FVector Direction = FRotator(0.f, Index * 90.f + FMath::FRandRange(-20.f, 20.f), 0.f).Vector();
			FActorSpawnParameters Spawn;
			Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			AStaticMeshActor* Chip = GetWorld()->SpawnActor<AStaticMeshActor>(GetActorLocation() + Direction * 28.f,
				FMath::VRand().Rotation(), Spawn);
			if (!Chip) continue;
			UStaticMeshComponent* ChipMesh = Chip->GetStaticMeshComponent();
			ChipMesh->SetMobility(EComponentMobility::Movable);
			ChipMesh->SetStaticMesh(CollectChipMesh);
			ChipMesh->SetWorldScale3D(FVector(FMath::FRandRange(.022f, .038f)));
			ChipMesh->SetCollisionProfileName(TEXT("PhysicsActor"));
			ChipMesh->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Ignore);
			ChipMesh->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
			ChipMesh->SetSimulatePhysics(true);
			ChipMesh->AddImpulse(Direction * 95.f + FVector(0.f,0.f,155.f), NAME_None, true);
			Chip->SetLifeSpan(1.35f);
		}
	}
}
