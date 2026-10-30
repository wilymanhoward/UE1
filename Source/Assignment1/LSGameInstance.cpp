// See LSGameInstance.h for this class's purpose and connections.

#include "LSGameInstance.h"

void ULSGameInstance::UnlockAllForms()
{
	UnlockForm(ESeedForm::Stone);
	UnlockForm(ESeedForm::Dandelion);
}
